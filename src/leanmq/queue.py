"""
Queue module for LeanMQ.

This module contains the Queue and QueueInfo classes for message queue operations.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import ResponseError

from leanmq.message import Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueueInfo:
    """Information about a queue.

    Attributes:
        name: Name of the queue
        is_dlq: Whether this queue is a dead letter queue
        message_count: Number of messages in the queue
        consumer_group: Name of the consumer group
        pending_messages: Number of pending messages
        created_at: Timestamp when queue was created
    """

    name: str
    is_dlq: bool = False
    message_count: int = 0
    consumer_group: Optional[str] = None
    pending_messages: int = 0
    created_at: Optional[float] = None


class Queue:
    """Represents a queue and provides operations on it.

    This class encapsulates operations on a Redis Stream including sending messages,
    receiving messages, deleting messages, and moving messages to a dead letter queue.
    """

    def __init__(
        self, client: redis.Redis, name: str, consumer_group: str, is_dlq: bool = False
    ) -> None:
        """
        Initialize a Queue object.

        Args:
            client: Redis client
            name: Name of the queue
            consumer_group: Name of the consumer group
            is_dlq: Whether this is a dead letter queue
        """
        self.client = client
        self.name = name
        self.consumer_group = consumer_group
        self.is_dlq = is_dlq
        self._ensure_consumer_group()

    def _ensure_consumer_group(self) -> None:
        """Ensure the consumer group exists."""
        try:
            self.client.xgroup_create(
                self.name, self.consumer_group, "$", mkstream=True
            )
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def get_info(self) -> QueueInfo:
        """Get information about the queue.

        Returns:
            QueueInfo object with queue metadata
        """
        # Get stream info
        info = self.client.xinfo_stream(self.name)

        # Get pending count
        try:
            pending = self.client.xpending(self.name, self.consumer_group)
            pending_count = pending["pending"] if pending else 0
        except ResponseError:
            pending_count = 0

        created_at = None
        if info["length"] > 0 and info.get("first-entry"):
            # Cast to float to satisfy type checker
            created_at = float(info["first-entry"][0])

        return QueueInfo(
            name=self.name,
            is_dlq=self.is_dlq,
            message_count=info["length"],
            consumer_group=self.consumer_group,
            pending_messages=pending_count,
            created_at=created_at,
        )

    def send_message(
        self,
        data: Dict[str, Any],
        message_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        Send a message to the queue.

        Args:
            data: Message data
            message_id: Optional message ID for metadata (UUID4 string). This is not
                used as the Redis stream ID, but stored in the message metadata for
                tracking purposes.
            ttl: Optional time-to-live in seconds

        Returns:
            Redis stream ID of the message
        """
        if message_id is None:
            message_id = str(uuid.uuid4())

        # Add metadata
        message_data = data.copy()
        message_data["_metadata"] = {
            "id": message_id,
            "timestamp": time.time(),
            "ttl": ttl,
        }

        # Serialize data
        serialized = json.dumps(message_data)

        # Add to stream
        result = self.client.xadd(
            self.name,
            {"data": serialized},
            id="*",  # Let Redis generate a valid stream ID
            maxlen=100000,  # Prevent unbounded growth
        )

        # Set expiry if TTL provided
        if ttl is not None:
            # Add message ID to a sorted set with expiry score
            expire_at = time.time() + ttl
            # Note: result now contains the Redis-generated ID
            self.client.zadd(f"{self.name}:expiry", {result: expire_at})

        # Return the Redis-generated ID instead of the UUID
        # This is important for operations that need the actual Redis stream ID
        # If it's bytes, decode it to a string
        if isinstance(result, bytes):
            return result.decode("utf-8")
        return result

    def get_messages(
        self,
        count: int = 1,
        block_for_seconds: Optional[int] = None,
        consumer_id: str = "default-consumer",
    ) -> List[Message]:
        """
        Get messages from the queue.

        Args:
            count: Number of messages to retrieve
            block_for_seconds: Time to block waiting for messages
            consumer_id: Consumer ID

        Returns:
            List of Message objects
        """
        block_ms = None if block_for_seconds is None else block_for_seconds * 1000

        result = self.client.xreadgroup(
            self.consumer_group,
            consumer_id,
            {self.name: ">"},
            count=count,
            block=block_ms,
        )

        messages = []
        if result:
            for _, message_list in result:
                for message_id, data in message_list:
                    try:
                        # Deserialize message
                        message_data_raw = data[b"data"]
                        if isinstance(message_data_raw, bytes):
                            message_data_str = message_data_raw.decode("utf-8")
                            message_data = json.loads(message_data_str)
                            metadata = message_data.pop("_metadata", {})

                            # Get delivery count
                            delivery_count = 0
                            try:
                                # Redis API changed, older versions used
                                #   min/max/count params
                                # Newer versions use a structured approach with
                                #   start/end/count
                                pending_info = self.client.xpending_range(
                                    self.name,
                                    self.consumer_group,
                                    message_id,  # Start ID
                                    message_id,  # End ID
                                    1,  # Count
                                )
                                if pending_info and len(pending_info) > 0:
                                    # Format varies, but we want the delivery counter
                                    delivery_count = pending_info[0].get(
                                        "times_delivered", 0
                                    )
                            except Exception as e:
                                logger.warning(f"Error getting pending info: {e}")

                            # Parse the message_id to ensure it's a string
                            msg_id = message_id
                            if isinstance(msg_id, bytes):
                                msg_id = msg_id.decode("utf-8")
                            else:
                                msg_id = str(msg_id)

                            messages.append(
                                Message(
                                    id=msg_id,  # Always use the Redis stream ID
                                    data=message_data,
                                    timestamp=metadata.get("timestamp", time.time()),
                                    delivery_count=delivery_count,
                                )
                            )
                    except Exception as e:
                        logger.error(f"Error parsing message {message_id}: {e}")
                        # Acknowledge bad messages to prevent reprocessing
                        self.client.xack(self.name, self.consumer_group, message_id)

        return messages

    def _validate_message_ids(self, message_ids: List[str]) -> List[str]:
        """
        Validate and normalize message IDs to ensure they are valid Redis stream IDs.

        Args:
            message_ids: List of message IDs to validate

        Returns:
            List of normalized and validated Redis stream IDs
        """
        if not message_ids:
            return []

        # Ensure we're using valid Redis stream IDs
        # Redis stream IDs must be in the format <timestamp>-<sequence>
        stream_ids = []
        for mid in message_ids:
            if isinstance(mid, bytes):
                # If it's bytes, decode it
                stream_ids.append(mid.decode("utf-8"))
            elif isinstance(mid, str):
                if (
                    "-" in mid
                    and mid.split("-")[0].isdigit()
                    and mid.split("-")[1].isdigit()
                ):
                    # This appears to be a valid Redis stream ID
                    # (timestamp-sequence format)
                    stream_ids.append(mid)
                else:
                    # Not a valid Redis stream ID, log a warning and skip it
                    logger.warning(f"Skipping invalid Redis stream ID: {mid}")
            else:
                logger.warning(f"Skipping message ID of unexpected type: {type(mid)}")

        if not stream_ids:
            logger.warning("No valid Redis stream IDs found")

        return stream_ids

    def acknowledge_messages(self, message_ids: List[str]) -> int:
        """
        Acknowledge messages as processed without removing them from the stream.
        This marks messages as processed by the consumer group but keeps them
        in the stream for history/auditing purposes.

        Use this method when you want to mark a message as successfully processed
        but still want to keep a record of it in the stream.

        Args:
            message_ids: List of message IDs to acknowledge

        Returns:
            Number of messages successfully acknowledged
        """
        if self.is_dlq:
            logger.warning(
                "Called acknowledge_messages on a DLQ. DLQ messages should be "
                "either deleted with delete_messages or requeued with requeue_messages."
            )
            return 0

        stream_ids = self._validate_message_ids(message_ids)
        if not stream_ids:
            return 0

        # Acknowledge messages
        ack_count = self.client.xack(self.name, self.consumer_group, *stream_ids)
        return ack_count

    def delete_messages(self, message_ids: List[str]) -> int:
        """
        Permanently delete messages from the queue.

        For regular queues, this will both acknowledge the messages and remove them
        from the stream. For DLQs, this just removes them from the stream.

        Args:
            message_ids: List of message IDs to delete

        Returns:
            Number of messages successfully deleted
        """
        stream_ids = self._validate_message_ids(message_ids)
        if not stream_ids:
            return 0

        # For regular queues, acknowledge messages first
        if not self.is_dlq:
            self.client.xack(self.name, self.consumer_group, *stream_ids)

        # Delete messages from the stream
        del_count = self.client.xdel(self.name, *stream_ids)

        # Delete from expiry set if exists
        expiry_key = f"{self.name}:expiry"
        if self.client.exists(expiry_key):
            self.client.zrem(expiry_key, *stream_ids)

        return del_count

    def requeue_messages(
        self, message_ids: List[str], destination_queue: "Queue"
    ) -> int:
        """
        Move messages from a DLQ back to their original queue for reprocessing.

        This method fetches messages from the DLQ, adds them to the destination
        queue, and then removes them from the DLQ.

        Args:
            message_ids: List of message IDs to requeue
            destination_queue: Queue to move messages to

        Returns:
            Number of messages successfully requeued
        """
        if not self.is_dlq:
            logger.warning(
                "Called requeue_messages on a non-DLQ. This method should only "
                "be used on a dead letter queue."
            )
            return 0

        if destination_queue.is_dlq:
            logger.warning(
                "Cannot requeue messages to another DLQ. "
                "Destination must be a regular queue."
            )
            return 0

        stream_ids = self._validate_message_ids(message_ids)
        if not stream_ids:
            return 0

        requeued_count = 0

        for mid in stream_ids:
            # Get the message from the stream
            messages = self.client.xrange(
                self.name,
                min=mid,
                max=mid,
                count=1,
            )

            if not messages:
                continue

            message_id, data = messages[0]

            try:
                # Parse message
                message_data_raw = data[b"data"]
                if isinstance(message_data_raw, bytes):
                    message_data_str = message_data_raw.decode("utf-8")
                    message_data = json.loads(message_data_str)
                    metadata = message_data.get("_metadata", {})

                    # Add requeue info
                    if "_requeues" not in message_data:
                        message_data["_requeues"] = []

                    message_data["_requeues"].append(
                        {
                            "timestamp": time.time(),
                            "from_dlq": self.name,
                            "to_queue": destination_queue.name,
                        }
                    )

                    # Send to destination queue
                    destination_queue.send_message(
                        message_data, message_id=metadata.get("id", str(uuid.uuid4()))
                    )

                    # Delete from DLQ
                    self.delete_messages([mid])

                    requeued_count += 1

            except Exception as e:
                logger.error(f"Error requeuing message {mid}: {e}")

        return requeued_count

    def purge(self) -> int:
        """
        Purge all messages from the queue.

        Returns:
            Number of messages purged
        """
        # Get current count
        info = self.client.xinfo_stream(self.name)
        count = info["length"]

        # Delete the stream and create it again
        self.client.delete(self.name)
        self.client.delete(f"{self.name}:expiry")

        # Recreate consumer group
        self._ensure_consumer_group()

        return count

    def move_to_dlq(self, message_ids: List[str], reason: str, dlq: "Queue") -> int:
        """
        Move messages to the dead letter queue.

        Args:
            message_ids: List of message IDs to move
            reason: Reason for moving to DLQ
            dlq: Dead letter queue object

        Returns:
            Number of messages moved
        """
        if not message_ids or not dlq or dlq.is_dlq is False:
            return 0

        moved_count = 0

        for mid in message_ids:
            # Validate Redis stream ID format
            valid_id = None
            if isinstance(mid, bytes):
                valid_id = mid.decode("utf-8")
            elif isinstance(mid, str):
                if (
                    "-" in mid
                    and mid.split("-")[0].isdigit()
                    and mid.split("-")[1].isdigit()
                ):
                    valid_id = mid
                else:
                    logger.warning(
                        f"Skipping invalid Redis stream ID in move_to_dlq: {mid}"
                    )
                    continue
            else:
                logger.warning(
                    "Skipping message ID of unexpected type in move_to_dlq: "
                    f"{type(mid)}"
                )
                continue

            # Get the message from the stream
            messages = self.client.xrange(
                self.name,
                min=valid_id,
                max=valid_id,
                count=1,
            )

            if not messages:
                continue

            message_id, data = messages[0]

            try:
                # Parse message
                message_data_raw = data[b"data"]
                if isinstance(message_data_raw, bytes):
                    message_data_str = message_data_raw.decode("utf-8")
                    message_data = json.loads(message_data_str)
                    metadata = message_data.get("_metadata", {})

                    # Add failure info
                    if "_failures" not in message_data:
                        message_data["_failures"] = []

                    message_data["_failures"].append(
                        {"timestamp": time.time(), "reason": reason}
                    )

                    # Send to DLQ
                    dlq.send_message(
                        message_data, message_id=metadata.get("id", str(uuid.uuid4()))
                    )

                    # Acknowledge from original queue
                    # (we've processed it by moving to DLQ)
                    self.acknowledge_messages([mid])

                    moved_count += 1

            except Exception as e:
                logger.error(f"Error moving message {mid} to DLQ: {e}")

        return moved_count
