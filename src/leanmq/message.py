"""
Message module for LeanMQ.

This module contains the Message class representing a message in the queue.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Message:
    """Representation of a message in the queue.
    
    Attributes:
        id: Unique identifier for the message. This is the Redis stream ID in
            the format '<timestamp>-<sequence>' (e.g., '1615456789012-0').
        data: Dictionary containing the message payload
        timestamp: Unix timestamp when message was created
        delivery_count: Number of times this message has been delivered
    """

    id: str
    data: Dict[str, Any]
    timestamp: float
    delivery_count: int = 0
