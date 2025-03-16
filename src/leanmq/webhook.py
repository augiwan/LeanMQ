"""
Webhook module for LeanMQ.

This module provides a webhook-like interface for internal microservice communication
using LeanMQ as the underlying message transport mechanism.
"""

import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from leanmq.core import LeanMQ
from leanmq.queue import Queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type for the decorated function
F = TypeVar("F", bound=Callable[..., Any])


class WebhookRoute:
    """Represents a registered webhook route.

    Attributes:
        path: The path pattern for the webhook
        handler: The function to call when a message arrives
        queue: The LeanMQ queue associated with this route
    """

    def __init__(
        self, path: str, handler: Callable[[Dict[str, Any]], Any], queue: Queue
    ) -> None:
        """Initialize a WebhookRoute.

        Args:
            path: The path pattern for the webhook
            handler: The function to call when a message arrives
            queue: The LeanMQ queue associated with this route
        """
        self.path = path
        self.handler = handler
        self.queue = queue


class LeanMQWebhook:
    """Webhook-like interface for internal microservice communication using LeanMQ.

    This class provides a convenient API for service-to-service communication using
    a webhook-like pattern, while leveraging LeanMQ's reliability features like
    dead letter queues, retries, and persistence.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        prefix: str = "webhook:",
        process_interval: int = 1,
        auto_start: bool = True,
    ) -> None:
        """Initialize the LeanMQWebhook.

        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database
            redis_password: Redis password
            prefix: Prefix for queue names
            process_interval: Interval in seconds for processing messages
            auto_start: Whether to start processing messages automatically
        """
        self.mq = LeanMQ(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            redis_password=redis_password,
            prefix=prefix,
        )
        self.routes: List[WebhookRoute] = []
        self.process_interval = process_interval
        self.is_processing = False

        if auto_start:
            # TODO: In a real implementation, start a background thread or process
            # to continuously process incoming messages
            pass

    def _normalize_path(self, path: str) -> str:
        """Normalize a path to ensure consistent formatting.

        Args:
            path: The path to normalize

        Returns:
            Normalized path
        """
        # Remove trailing slash if present, unless it's the root path
        if path != "/" and path.endswith("/"):
            path = path[:-1]

        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"

        return path

    def _path_to_queue_name(self, path: str) -> str:
        """Convert a path to a queue name.

        Args:
            path: The path to convert

        Returns:
            Queue name
        """
        # Remove leading and trailing slashes
        path = path.strip("/")
        # Replace remaining slashes with underscores
        path = path.replace("/", "_")
        # Replace any non-alphanumeric characters with underscores
        path = "".join(c if c.isalnum() else "_" for c in path)
        return path

    def get(self, path: str) -> Callable[[F], F]:
        """Decorator for registering a webhook handler.

        Args:
            path: The path pattern for the webhook

        Returns:
            Decorator function
        """
        normalized_path = self._normalize_path(path)
        queue_name = self._path_to_queue_name(normalized_path)

        def decorator(func: F) -> F:
            # Create queue pair for this path
            main_queue, _ = self.mq.create_queue_pair(queue_name)

            # Register the route
            self.routes.append(WebhookRoute(normalized_path, func, main_queue))

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)

            return cast(F, wrapper)

        return decorator

    def send(self, path: str, data: Dict[str, Any]) -> str:
        """Send a webhook event.

        Args:
            path: The target path for the webhook
            data: The data to send

        Returns:
            Message ID
        """
        normalized_path = self._normalize_path(path)
        queue_name = self._path_to_queue_name(normalized_path)

        # Get or create the queue
        try:
            main_queue = self.mq.get_queue(queue_name)
            if main_queue is None:
                main_queue, _ = self.mq.create_queue_pair(queue_name)
        except Exception as e:
            logger.error(f"Error creating queue for {path}: {e}")
            raise

        # Add webhook metadata
        message_data = data.copy()
        message_data["_leanmq"] = {
            "webhook": {
                "path": normalized_path,
                "timestamp": time.time(),
            }
        }

        # Send the message
        message_id = main_queue.send_message(message_data)
        return message_id

    def process_messages(self, block: bool = False, timeout: int = 1) -> int:
        """Process incoming webhook messages.

        Args:
            block: Whether to block waiting for messages
            timeout: How long to block for in seconds

        Returns:
            Number of messages processed
        """
        if self.is_processing and block:
            logger.warning("Already processing messages")
            return 0

        try:
            self.is_processing = True
            processed_count = 0

            for route in self.routes:
                try:
                    # Get messages from the queue
                    messages = route.queue.get_messages(
                        count=10, block_for_seconds=timeout if block else None
                    )

                    for message in messages:
                        try:
                            # Call the handler with the message data
                            route.handler(message.data)

                            # Acknowledge the message
                            route.queue.acknowledge_messages([message.id])
                            processed_count += 1
                        except Exception as e:
                            logger.error(f"Error processing message {message.id}: {e}")
                            # TODO: Implement retry logic with backoff

                            # Move to DLQ after processing failure
                            dlq = self.mq.get_dead_letter_queue(
                                self._path_to_queue_name(route.path)
                            )
                            if dlq:
                                route.queue.move_to_dlq(
                                    [message.id], f"Processing error: {e}", dlq
                                )
                except Exception as e:
                    logger.error(f"Error fetching messages for route {route.path}: {e}")

            return processed_count
        finally:
            self.is_processing = False

    def start_processing(self) -> None:
        """Start processing messages in a loop.

        In a real implementation, this would start a background thread or process.
        """
        # This is a simple synchronous implementation
        # In a real application, you would use threading or asyncio
        self.is_processing = True
        try:
            while self.is_processing:
                self.process_messages(block=True, timeout=self.process_interval)
        except KeyboardInterrupt:
            logger.info("Stopping message processing")
        finally:
            self.is_processing = False

    def stop_processing(self) -> None:
        """Stop processing messages."""
        self.is_processing = False

    def close(self) -> None:
        """Close connections."""
        self.mq.close()

    def __enter__(self) -> "LeanMQWebhook":
        """Support with statement."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close connections when exiting with statement."""
        self.close()
