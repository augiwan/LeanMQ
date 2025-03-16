# LeanMQ

![GitHub Repo stars](https://img.shields.io/github/stars/augiwan/LeanMQ?style=social)
![GitHub license](https://img.shields.io/github/license/augiwan/LeanMQ)
![PyPI - Downloads](https://img.shields.io/pypi/dm/LeanMQ)
![Python Version](https://img.shields.io/pypi/pyversions/LeanMQ)
![PyPI](https://img.shields.io/pypi/v/LeanMQ)
![PyPI - Status](https://img.shields.io/pypi/status/LeanMQ)
![Code style: Ruff](https://img.shields.io/badge/code%20style-Ruff-261230.svg)
![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)

LeanMQ is a lightweight, Redis-based message queue for microservice communication. It provides a simple but powerful implementation using Redis Streams with support for dead-letter queues, message TTL, atomic transactions, consumer groups, and message retry tracking.

<hr />

### 🔥 Just getting started – show your support!
> If you find LeanMQ interesting, consider giving it a ⭐ star on GitHub!  
> It helps others discover it and motivates ongoing improvements.

<hr />

## Features

- **Dead Letter Queues**: Automatic handling of failed messages
- **Message TTL**: Set expiration times for messages
- **Atomic Transactions**: Send multiple messages in a single transaction
- **Consumer Groups**: Support for multiple consumers
- **Message Tracking**: Track delivery attempts and failures
- **Lightweight**: Simple API with minimal dependencies

## Installation

```bash
pip install leanmq
```

## Quick Start

```python
from leanmq import LeanMQ

# Initialize message queue
mq = LeanMQ(redis_host="localhost", redis_port=6379)

# Create a queue pair (main queue and dead letter queue)
main_queue, dlq = mq.create_queue_pair("notifications")

# Send a message
message_id = main_queue.send_message(
    {"type": "email", "recipient": "user@example.com"}
)

# Send messages in a transaction
with mq.transaction() as tx:
    tx.send_message(main_queue, {"type": "email", "recipient": "user1@example.com"})
    tx.send_message(main_queue, {"type": "sms", "recipient": "+1234567890"})

# Receive messages
messages = main_queue.get_messages(count=5, block_for_seconds=1)

# Process messages
for msg in messages:
    try:
        print(f"Processing message: {msg.id} - {msg.data}")
        # Your processing logic here...

        # Acknowledge successful processing (keeps message in stream for history)
        main_queue.acknowledge_messages([msg.id])
    except Exception as e:
        # Move to DLQ if processing fails
        main_queue.move_to_dlq([msg.id], f"Processing error: {e}", dlq)

# Clean up
mq.close()
```

## Usage Guide

### Initializing LeanMQ

```python
from leanmq import LeanMQ

# Basic initialization
mq = LeanMQ()

# With custom Redis connection
mq = LeanMQ(
    redis_host="redis.example.com",
    redis_port=6379,
    redis_db=0,
    redis_password="password",
    prefix="myapp:",
    max_retries=3
)

# Using with statement for automatic cleanup
with LeanMQ() as mq:
    # your code here
    pass  # Connection will be closed automatically
```

### Working with Queues

```python
# Create a new queue with its dead letter queue
main_queue, dlq = mq.create_queue_pair("orders")

# Get an existing queue
queue = mq.get_queue("orders")

# Get the associated dead letter queue
dlq = mq.get_dead_letter_queue("orders")

# List all queues
queues = mq.list_queues()
for q in queues:
    print(f"Queue: {q.name}, Messages: {q.message_count}, DLQ: {q.is_dlq}")

# Delete a queue
mq.delete_queue("orders", delete_dlq=True)
```

### Sending Messages

```python
# Basic message sending
message_id = queue.send_message({"order_id": "12345", "status": "new"})

# With custom message ID
message_id = queue.send_message(
    {"order_id": "12345", "status": "new"},
    message_id="custom-id-123"
)

# With time-to-live (TTL) in seconds
message_id = queue.send_message(
    {"order_id": "12345", "status": "new"},
    ttl=3600  # Message will expire after 1 hour
)
```

### Receiving and Processing Messages

```python
# Get up to 10 messages
messages = queue.get_messages(count=10)

# Block for messages if none are immediately available
messages = queue.get_messages(count=5, block_for_seconds=5)

# Specify consumer ID (useful for load balancing)
messages = queue.get_messages(count=10, consumer_id="worker-1")

# Process and acknowledge messages
for msg in messages:
    try:
        # Process the message
        process_order(msg.data)
        
        # Acknowledge successful processing (keeps message in stream for history/auditing)
        queue.acknowledge_messages([msg.id])
        
        # Or completely remove the message from the stream
        # queue.delete_messages([msg.id])
    except Exception as e:
        # If processing fails, move to dead letter queue
        queue.move_to_dlq([msg.id], f"Error: {str(e)}", dlq)
```

### Managing Dead Letter Queue (DLQ) Messages

```python
# Get messages from DLQ
dlq_messages = dlq.get_messages(count=10)

# Permanently delete a message from DLQ
dlq.delete_messages([dlq_messages[0].id])

# Requeue a message back to the main queue for retry
dlq.requeue_messages([dlq_messages[1].id], main_queue)
```

### Using Transactions

```python
# Start a transaction to send multiple messages atomically
with mq.transaction() as tx:
    # Add messages to the transaction
    tx.send_message(queue1, {"key": "value1"})
    tx.send_message(queue2, {"key": "value2"})
    # Transaction will be committed at the end of the block
```

### Queue Management

```python
# Get information about a queue
info = queue.get_info()
print(f"Queue name: {info.name}")
print(f"Message count: {info.message_count}")
print(f"Pending messages: {info.pending_messages}")

# Purge all messages from a queue
purged_count = queue.purge()
print(f"Purged {purged_count} messages")

# Process expired messages across all queues
expired_count = mq.process_expired_messages()
print(f"Processed {expired_count} expired messages")
```

## License

Apache 2.0 - see LICENSE.md for details.

## Copyright

Copyright (c) 2025 Augustus D'Souza
