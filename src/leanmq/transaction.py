"""
Transaction module for LeanMQ.

This module contains the Transaction class for atomic operations.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import redis

# Circular import is avoided by using string type annotation
from leanmq.queue import Queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Transaction:
    """Represents a Redis transaction for atomic operations.
    
    This class allows multiple queue operations to be executed atomically
    within a Redis transaction.
    """

    def __init__(self, client: redis.Redis) -> None:
        """
        Initialize a Transaction.

        Args:
            client: Redis client
        """
        self.client = client
        self.pipeline: Optional[redis.client.Pipeline] = None
        self.messages: List[Tuple[Queue, Dict[str, Any], str, Optional[int]]] = []

    def send_message(
        self,
        queue: Queue,
        data: Dict[str, Any],
        message_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        Add a message send operation to the transaction.

        Args:
            queue: Queue to send to
            data: Message data
            message_id: Optional message ID for metadata (UUID4 string). This is not used as the Redis stream ID,
                      but stored in the message metadata for tracking purposes.
            ttl: Optional time-to-live in seconds

        Returns:
            Internal tracking ID (not the actual Redis stream ID that will be generated when the transaction completes)
        """
        if message_id is None:
            message_id = str(uuid.uuid4())

        # Track operation for execution
        self.messages.append((queue, data, message_id, ttl))
        return message_id

    def _execute(self) -> None:
        """Execute the transaction."""
        if not self.pipeline:
            return

        # Add all operations to pipeline
        messages_with_ttl = []
        results = None

        # Add all operations to pipeline
        for queue, data, message_id, ttl in self.messages:
            # Add metadata
            message_data = data.copy()
            message_data["_metadata"] = {
                "id": message_id,
                "timestamp": time.time(),
                "ttl": ttl,
            }

            # Serialize data
            serialized = json.dumps(message_data)

            # Add to stream with auto-generated ID
            self.pipeline.xadd(
                queue.name, {"data": serialized}, id="*", maxlen=100000
            )
            
            # Track which messages have TTL for post-processing
            if ttl is not None:
                messages_with_ttl.append((queue, ttl, len(self.messages) - 1))

        # Execute pipeline
        results = self.pipeline.execute()
        
        # Handle TTL for messages after we have their IDs
        if messages_with_ttl and results:
            # Create a new pipeline for TTL operations
            ttl_pipeline = self.client.pipeline()
            
            for queue, ttl, idx in messages_with_ttl:
                if idx < len(results):
                    # Get the Redis-generated ID from results
                    redis_id = results[idx]
                    # Set expiry
                    expire_at = time.time() + ttl
                    ttl_pipeline.zadd(f"{queue.name}:expiry", {redis_id: expire_at})
            
            # Execute TTL operations
            ttl_pipeline.execute()
