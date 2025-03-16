# Message API Reference

This reference documents the Message class in LeanMQ.

## Message Class

The `Message` class represents a message in a queue. Messages are returned when you call `queue.get_messages()` and contain both the message data and metadata about the message.

### Attributes

- `id` (str): Unique identifier for the message. This is the Redis stream ID in the format `{timestamp}-{sequence}` (e.g., '1615456789012-0').
- `data` (Dict[str, Any]): Dictionary containing the message payload.
- `timestamp` (float): Unix timestamp when message was created.
- `delivery_count` (int): Number of times this message has been delivered.

### Constructor

```python
Message(
    id: str,
    data: Dict[str, Any],
    timestamp: Optional[float] = None,
    delivery_count: int = 0
)
```

**Parameters**:
- `id` (str): Unique identifier for the message
- `data` (Dict[str, Any]): Message payload
- `timestamp` (Optional[float]): Unix timestamp when message was created
- `delivery_count` (int): Number of times this message has been delivered

::: warning
You should not create Message objects directly. They are created by the `get_messages()` method of the Queue class.
:::

## Working with Messages

### Getting Messages

Messages are retrieved from a queue using the `get_messages()` method:

```python
from leanmq import LeanMQ

# Initialize LeanMQ
mq = LeanMQ(redis_host="localhost", redis_port=6379)

# Get a queue
queue = mq.get_queue("notifications")

# Get messages from the queue
messages = queue.get_messages(count=10, block_for_seconds=5)

# Process the messages
for message in messages:
    print(f"Message ID: {message.id}")
    print(f"Data: {message.data}")
    print(f"Timestamp: {message.timestamp}")
    print(f"Delivery count: {message.delivery_count}")
    
    # Process the message...
    
    # Acknowledge successful processing
    queue.acknowledge_messages([message.id])
```

### Message Structure

The `data` attribute of a Message contains the actual payload that was sent to the queue. This is a Python dictionary that you can access directly:

```python
# Access message data
message = messages[0]
user_id = message.data.get("user_id")
notification_type = message.data.get("type")
content = message.data.get("content")

print(f"Notification for user {user_id}: {notification_type}")
print(f"Content: {content}")
```

### Message IDs

The `id` attribute is a unique identifier for the message in the Redis stream. It's in the format `{timestamp}-{sequence}` and is used when acknowledging, deleting, or moving messages:

```python
# Get messages
messages = queue.get_messages(count=5)

# Collect message IDs
message_ids = [message.id for message in messages]

# Use the IDs with queue operations
queue.acknowledge_messages(message_ids)
```

### Message Timestamps

The `timestamp` attribute indicates when the message was created, as a Unix timestamp (seconds since epoch):

```python
import time
from datetime import datetime

# Get a message
message = queue.get_messages(count=1)[0]

# Convert timestamp to readable datetime
created_at = datetime.fromtimestamp(message.timestamp)
print(f"Message created at: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")

# Check how old the message is
age_seconds = time.time() - message.timestamp
print(f"Message age: {age_seconds:.2f} seconds")
```

### Delivery Count

The `delivery_count` attribute tracks how many times a message has been delivered to consumers. This is useful for implementing retry logic with backoff:

```python
# Get messages
messages = queue.get_messages(count=10)

for message in messages:
    print(f"Message ID: {message.id}, Delivery count: {message.delivery_count}")
    
    try:
        # Process the message
        process_message(message.data)
        
        # Acknowledge success
        queue.acknowledge_messages([message.id])
    except Exception as e:
        # Implement retry logic with backoff
        if message.delivery_count >= 3:
            # After 3 failures, move to DLQ
            dlq = mq.get_dead_letter_queue("myqueue")
            queue.move_to_dlq([message.id], f"Failed after {message.delivery_count} attempts: {e}", dlq)
        else:
            # Let it be redelivered (don't acknowledge)
            print(f"Processing failed, will retry. Attempt: {message.delivery_count}")
```

## Example: Message Processing Patterns

### Basic Processing

```python
# Get messages
messages = queue.get_messages(count=10)

# Process each message
for message in messages:
    try:
        result = process_message(message.data)
        print(f"Processed message {message.id}: {result}")
        
        # Acknowledge successful processing
        queue.acknowledge_messages([message.id])
    except Exception as e:
        print(f"Error processing message {message.id}: {e}")
        # Move to DLQ
        dlq = mq.get_dead_letter_queue("myqueue")
        queue.move_to_dlq([message.id], f"Processing error: {e}", dlq)
```

### Batch Processing

```python
# Get messages
messages = queue.get_messages(count=100)

if not messages:
    print("No messages to process")
else:
    try:
        # Extract data for batch processing
        batch_data = [message.data for message in messages]
        
        # Process in batch
        results = batch_process_messages(batch_data)
        
        # Acknowledge all successful messages
        queue.acknowledge_messages([message.id for message in messages])
        
        print(f"Processed {len(messages)} messages in batch")
    except Exception as e:
        print(f"Batch processing failed: {e}")
        # In case of batch failure, move all to DLQ
        dlq = mq.get_dead_letter_queue("myqueue")
        queue.move_to_dlq([m.id for m in messages], f"Batch processing error: {e}", dlq)
```

### Priority-Based Processing

```python
# Process messages based on priority field
messages = queue.get_messages(count=20)

# Sort messages by priority (if available)
sorted_messages = sorted(
    messages,
    key=lambda m: m.data.get("priority", 5),  # Default to medium priority (5)
    reverse=True  # Higher numbers = higher priority
)

# Process in priority order
for message in sorted_messages:
    priority = message.data.get("priority", 5)
    print(f"Processing message with priority {priority}: {message.id}")
    
    # Process the message...
    
    # Acknowledge when done
    queue.acknowledge_messages([message.id])
```

### Message Filtering

```python
# Get messages but only process those matching certain criteria
messages = queue.get_messages(count=50)

# Filter messages
important_messages = [
    message for message in messages
    if message.data.get("user_type") == "premium" or message.data.get("urgent", False)
]

# Process important messages first
for message in important_messages:
    process_message(message.data)
    queue.acknowledge_messages([message.id])

# Then process the rest
other_messages = [m for m in messages if m not in important_messages]
for message in other_messages:
    process_message(message.data)
    queue.acknowledge_messages([message.id])
```

## Related

- [Queue API](./queue.md): Documentation for the Queue class that processes messages
- [Core API](./core.md): Documentation for the LeanMQ class that manages queues
