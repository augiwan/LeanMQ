"""
Core module for LeanMQ.

This module contains the main LeanMQ class, formerly known as RedisMessageQueue.
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple

import backoff
import redis
from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from leanmq.queue import Queue, QueueInfo
from leanmq.transaction import Transaction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeanMQ:
    """Redis-based message queue with robust error handling and dead letter queues.

    This is the main entry point for the LeanMQ library, providing methods for
    creating queues, sending messages, and managing transactions.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        prefix: str = "mq:",
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the LeanMQ.

        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database
            redis_password: Redis password
            prefix: Prefix for queue names
            max_retries: Maximum number of retry attempts for operations
        """
        self.prefix = prefix
        self.max_retries = max_retries

        # Create connection pool
        self.pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            socket_timeout=5.0,
            socket_keepalive=True,
            retry_on_timeout=True,
            decode_responses=False,  # Keep as bytes for more control
            max_connections=10,
        )

        # Create Redis client
        self.client = self._get_redis_client()

        # Track queues
        self._queue_registry_key = f"{self.prefix}registry"

    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, TimeoutError),
        max_tries=3,
        jitter=backoff.full_jitter,
    )
    def _get_redis_client(self) -> redis.Redis:
        """Get a Redis client with exponential backoff for retries."""
        return redis.Redis(connection_pool=self.pool)

    def create_queue_pair(self, queue_name: str) -> Tuple[Queue, Queue]:
        """
        Create a queue and its corresponding dead letter queue.

        Args:
            queue_name: Base name for the queue

        Returns:
            Tuple of (main_queue, dlq)
        """
        main_name = f"{self.prefix}{queue_name}"
        dlq_name = f"{self.prefix}{queue_name}:dlq"
        group_name = f"{queue_name}-group"

        # Create the main queue and DLQ
        main_queue = Queue(self.client, main_name, group_name)
        dlq = Queue(self.client, dlq_name, f"{group_name}-dlq", is_dlq=True)

        # Register queues
        self.client.sadd(self._queue_registry_key, main_name, dlq_name)

        # Store metadata
        self.client.hset(
            f"{main_name}:metadata",
            mapping={
                "created_at": str(time.time()),
                "dlq": dlq_name,
                "consumer_group": group_name,
            },
        )

        self.client.hset(
            f"{dlq_name}:metadata",
            mapping={
                "created_at": str(time.time()),
                "main_queue": main_name,
                "consumer_group": f"{group_name}-dlq",
                "is_dlq": "true",
            },
        )

        return main_queue, dlq

    def list_queues(self) -> List[QueueInfo]:
        """
        List all queues.

        Returns:
            List of QueueInfo objects
        """
        queues = []
        queue_names_set = self.client.smembers(self._queue_registry_key)
        queue_names = [
            name.decode("utf-8") if isinstance(name, bytes) else str(name)
            for name in queue_names_set
        ]

        for name_str in queue_names:
            try:
                metadata_key = f"{name_str}:metadata"

                if not self.client.exists(metadata_key):
                    continue

                metadata_dict = self.client.hgetall(metadata_key)
                metadata = {}
                for k, v in metadata_dict.items():
                    key = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                    value = v.decode("utf-8") if isinstance(v, bytes) else str(v)
                    metadata[key] = value

                is_dlq = metadata.get("is_dlq") == "true"
                consumer_group = metadata.get("consumer_group", "default-group")

                try:
                    # Get info
                    info = self.client.xinfo_stream(name_str)
                    message_count = info["length"]

                    # Get pending count
                    try:
                        pending = self.client.xpending(name_str, consumer_group)
                        pending_count = pending["pending"] if pending else 0
                    except ResponseError:
                        pending_count = 0

                    # Add to list
                    created_at_str = metadata.get("created_at", "0")
                    created_at = float(created_at_str) if created_at_str else 0.0

                    queues.append(
                        QueueInfo(
                            name=name_str,
                            is_dlq=is_dlq,
                            message_count=message_count,
                            consumer_group=consumer_group,
                            pending_messages=pending_count,
                            created_at=created_at,
                        )
                    )
                except ResponseError:
                    # Stream doesn't exist yet
                    created_at_str = metadata.get("created_at", "0")
                    created_at = float(created_at_str) if created_at_str else 0.0

                    queues.append(
                        QueueInfo(
                            name=name_str,
                            is_dlq=is_dlq,
                            consumer_group=consumer_group,
                            created_at=created_at,
                        )
                    )
            except Exception as e:
                logger.error(f"Error getting queue info for {name_str}: {e}")

        return queues

    def delete_queue(self, queue_name: str, delete_dlq: bool = True) -> bool:
        """
        Delete a queue and optionally its DLQ.

        Args:
            queue_name: Name of the queue to delete
            delete_dlq: Whether to also delete the DLQ

        Returns:
            Success boolean
        """
        queue_name = f"{self.prefix}{queue_name}"
        metadata_key = f"{queue_name}:metadata"

        try:
            # Get DLQ if needed
            dlq_name = None
            if delete_dlq and self.client.exists(metadata_key):
                dlq_raw = self.client.hget(metadata_key, "dlq")
                if dlq_raw:
                    dlq_name = (
                        dlq_raw.decode("utf-8")
                        if isinstance(dlq_raw, bytes)
                        else str(dlq_raw)
                    )

            # Delete main queue
            self.client.delete(queue_name, metadata_key, f"{queue_name}:expiry")
            self.client.srem(self._queue_registry_key, queue_name)

            # Delete DLQ if requested
            if delete_dlq and dlq_name:
                self.client.delete(
                    dlq_name, f"{dlq_name}:metadata", f"{dlq_name}:expiry"
                )
                self.client.srem(self._queue_registry_key, dlq_name)

            return True
        except Exception as e:
            logger.error(f"Error deleting queue {queue_name}: {e}")
            return False

    def get_queue(self, queue_name: str) -> Optional[Queue]:
        """
        Get a queue object.

        Args:
            queue_name: Name of the queue

        Returns:
            Queue object or None if not found
        """
        full_name = f"{self.prefix}{queue_name}"
        metadata_key = f"{full_name}:metadata"

        if not self.client.exists(metadata_key):
            return None

        metadata_dict = self.client.hgetall(metadata_key)
        metadata: Dict[str, str] = {}

        for k, v in metadata_dict.items():
            key = k.decode("utf-8") if isinstance(k, bytes) else str(k)
            value = v.decode("utf-8") if isinstance(v, bytes) else str(v)
            metadata[key] = value

        consumer_group = metadata.get("consumer_group", "default-group")
        is_dlq = metadata.get("is_dlq") == "true"

        return Queue(self.client, full_name, consumer_group, is_dlq)

    def get_dead_letter_queue(self, queue_name: str) -> Optional[Queue]:
        """
        Get the DLQ for a queue.

        Args:
            queue_name: Name of the main queue

        Returns:
            DLQ object or None if not found
        """
        main_queue = self.get_queue(queue_name)
        if not main_queue:
            return None

        metadata_key = f"{main_queue.name}:metadata"

        if not self.client.exists(metadata_key):
            return None

        dlq_raw = self.client.hget(metadata_key, "dlq")
        if not dlq_raw:
            return None

        dlq_name = (
            dlq_raw.decode("utf-8") if isinstance(dlq_raw, bytes) else str(dlq_raw)
        )
        dlq_metadata_key = f"{dlq_name}:metadata"

        if not self.client.exists(dlq_metadata_key):
            return None

        metadata_dict = self.client.hgetall(dlq_metadata_key)
        metadata: Dict[str, str] = {}

        for k, v in metadata_dict.items():
            key = k.decode("utf-8") if isinstance(k, bytes) else str(k)
            value = v.decode("utf-8") if isinstance(v, bytes) else str(v)
            metadata[key] = value

        consumer_group = metadata.get("consumer_group", f"{queue_name}-group-dlq")

        return Queue(self.client, dlq_name, consumer_group, is_dlq=True)

    @contextmanager
    def transaction(self) -> Iterator[Transaction]:
        """
        Start a transaction for atomic operations.

        Returns:
            Transaction object

        Example:
            with queue_manager.transaction() as tx:
                tx.send_message(queue1, {"key": "value"})
                tx.send_message(queue2, {"another": "message"})
        """
        tx = Transaction(self.client)
        tx.pipeline = self.client.pipeline(transaction=True)

        try:
            yield tx
            tx._execute()
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            tx.pipeline = None

    def process_expired_messages(self) -> int:
        """
        Process expired messages (those with TTL) across all queues.

        Returns:
            Number of expired messages processed
        """
        count = 0
        queues = self.list_queues()
        now = time.time()

        for queue_info in queues:
            expiry_key = f"{queue_info.name}:expiry"

            # Check if expiry set exists
            if not self.client.exists(expiry_key):
                continue

            # Get expired message IDs
            expired_set = self.client.zrangebyscore(expiry_key, 0, now)
            expired = [
                msg.decode("utf-8") if isinstance(msg, bytes) else str(msg)
                for msg in expired_set
            ]

            if not expired:
                continue

            # Delete expired messages
            for message_id in expired:
                try:
                    self.client.xdel(queue_info.name, message_id)
                    self.client.zrem(expiry_key, message_id)
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting expired message {message_id}: {e}")

        return count

    def close(self) -> None:
        """Close Redis connections."""
        self.pool.disconnect()

    def __enter__(self) -> "LeanMQ":
        """Support with statement."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close connections when exiting with statement."""
        self.close()
