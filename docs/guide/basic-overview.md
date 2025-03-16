# Basic Overview

## Core Concepts

Before diving into code, let's understand a few key concepts:

- **Queue**: A named stream where messages are stored and processed
- **Message**: Data sent between services, stored in a queue
- **Dead Letter Queue (DLQ)**: A special queue where failed messages are moved
- **Consumer Group**: A group of consumers that process messages together
- **Transaction**: A way to perform multiple operations atomically

## Basic Usage: Core API

Let's start with the core functionality of creating queues and sending messages:

```python
from leanmq import LeanMQ

# Initialize the LeanMQ client
mq = LeanMQ(
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    prefix="myapp:"  # Optional prefix for queue names
)

# Create a queue (and its corresponding dead letter queue)
main_queue, dlq = mq.create_queue_pair("notifications")

# Send a message to the queue
message_id = main_queue.send_message({"user_id": 123, "message": "Hello, world!"})
print(f"Sent message with ID: {message_id}")

# Get messages from the queue
messages = main_queue.get_messages(count=10)
for message in messages:
    print(f"Received message: {message.data}")
    
    # Process the message (your business logic here)
    # ...
    
    # Acknowledge successful processing
    main_queue.acknowledge_messages([message.id])
```

## Using the Webhook Pattern

LeanMQ provides a webhook-like interface that's more intuitive for service-to-service communication:

```python
from leanmq import LeanMQWebhook
import time

# Initialize the webhook client
webhook = LeanMQWebhook(
    redis_host="localhost",
    redis_port=6379,
    redis_db=0
)

# Register a webhook handler
@webhook.get("/users/created/")
def handle_user_created(data):
    print(f"New user created: {data['username']}")
    # Your processing logic here...

# Send a webhook event
webhook.send(
    "/users/created/",
    {
        "user_id": 456,
        "username": "johndoe",
        "email": "john@example.com",
        "created_at": time.time()
    }
)

# Process incoming webhooks (in a real app, you'd run this in a separate process or thread)
webhook.process_messages(block=True, timeout=5)
```

## Running a Webhook Service

For continuous processing of webhook events, LeanMQ provides a convenient way to run a webhook service:

```python
from leanmq import LeanMQWebhook
import time

# Initialize and set up your webhook handlers
webhook = LeanMQWebhook(redis_host="localhost", redis_port=6379, redis_db=0)

@webhook.get("/order/status/")
def handle_order_status(data):
    print(f"Order {data['order_id']} status updated to: {data['status']}")

# Run the webhook service (starts a background thread)
service = webhook.run_service(
    process_count=10,        # Process up to 10 messages per iteration
    block_for_seconds=1,     # Wait up to 1 second for new messages
    handle_signals=True,     # Register signal handlers for graceful shutdown
)

print("Webhook service is running...")

# In a real app, your main process would do other work here
# For this example, we'll just keep the service running for a while
try:
    while service.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
finally:
    # Stop the service when done
    service.stop()
    webhook.close()
```

## Error Handling

LeanMQ automatically handles many error scenarios for you. Failed messages are moved to a dead letter queue for later inspection or reprocessing:

```python
# Get messages from the dead letter queue
dlq = mq.get_dead_letter_queue("notifications")
failed_messages = dlq.get_messages(count=10)

for message in failed_messages:
    print(f"Failed message: {message.data}")
    print(f"Delivery attempts: {message.delivery_count}")
    
    # You can requeue messages from the DLQ back to the main queue
    dlq.requeue_messages([message.id], main_queue)
```

## Using Transactions

For operations that need to be atomic (all succeed or all fail), use transactions:

```python
# Create multiple queues
notifications_queue, _ = mq.create_queue_pair("notifications")
audit_queue, _ = mq.create_queue_pair("audit")

# Start a transaction
with mq.transaction() as tx:
    # Add multiple send operations to the transaction
    tx.send_message(notifications_queue, {"user_id": 123, "message": "Account updated"})
    tx.send_message(audit_queue, {"action": "account_update", "user_id": 123})
    
    # All messages will be sent atomically when the transaction block exits
```