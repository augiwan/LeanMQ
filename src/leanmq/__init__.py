"""
LeanMQ: A lightweight, Redis-based message queue for microservice communication.

This package provides a simple but powerful message queue implementation
based on Redis Streams with support for:
- Dead-letter queues
- Message TTL (time-to-live)
- Atomic transactions
- Consumer groups
- Message retry tracking
"""

__version__ = "0.1.0"

from leanmq.core import LeanMQ
from leanmq.message import Message
from leanmq.queue import Queue, QueueInfo
from leanmq.transaction import Transaction
from leanmq.webhook import LeanMQWebhook, WebhookService

__all__ = ["LeanMQ", "Message", "Queue", "QueueInfo", "Transaction", "LeanMQWebhook", "WebhookService"]
