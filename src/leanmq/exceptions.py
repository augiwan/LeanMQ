"""
Exceptions module for LeanMQ.

This module contains custom exceptions used by the LeanMQ library.
"""


class LeanMQError(Exception):
    """Base exception for all LeanMQ errors."""
    pass


class ConnectionError(LeanMQError):
    """Raised when there is an error connecting to Redis."""
    pass


class QueueError(LeanMQError):
    """Raised when there is an error with a queue operation."""
    pass


class MessageError(LeanMQError):
    """Raised when there is an error processing a message."""
    pass


class TransactionError(LeanMQError):
    """Raised when there is an error in a transaction."""
    pass


class QueueNotFoundError(QueueError):
    """Raised when a queue cannot be found."""
    pass


class DeadLetterQueueNotFoundError(QueueError):
    """Raised when a dead letter queue cannot be found."""
    pass
