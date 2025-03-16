# Queue API Reference

This reference documents the Queue-related classes and methods in LeanMQ.

## Queue Class

The `Queue` class represents a message queue and provides operations for sending, receiving, and managing messages.

### Constructor

```python
Queue(
    name: str,
    redis_connection: Redis,
    is_dlq: bool = False,
    consumer_group: Optional[str] = None
)
```

**Parameters**:
- `name` (str): Name of the queue
- `redis_connection` (Redis): Redis connection to use
- `is_dlq` (bool): Whether this queue is a dead letter queue
- `consumer_group` (Optional[str]): Name of the consumer group to use

::: warning
You should not create Queue objects directly. Instead, use the `create_queue_pair()`, `get_queue()`, or `get_dead_letter_queue()` methods of the LeanMQ class.
:::

### Methods

#### `send_message`

```python
send_message(
    data: Dict[str, Any],
    ttl_seconds: Optional[int] = None
) -> str
```

Send a message to the queue.

**Parameters**:
- `data` (Dict[str, Any]): Message data
- `ttl_seconds` (Optional[int]): Time-to-live for the message in seconds

**Returns**: Message ID

**Example**:
```python
message_id = queue.send_message({"key": "value"})
print(f"Sent message with ID: {message_id}")

# Send a message that expires after 1 hour
ttl_seconds = 60 * 60
message_id = queue.send_message({"key": "value"}, ttl_seconds=ttl_seconds)
```

#### `get_messages`

```python
get_messages(
    count: int = 1,
    block_for_seconds: Optional[float] = None,
    consumer_id: str = "consumer1"
) -> List[Message]
```

Get messages from the queue.

**Parameters**:
- `count` (int): Maximum number of messages to get
- `block_for_seconds` (Optional[float]): How long to block waiting for messages
- `consumer_id` (str): ID of the consumer getting messages

**Returns**: List of Message objects

**Example**:
```python
# Get up to 10 messages, waiting up to 5 seconds for new messages
messages = queue.get_messages(count=10, block_for_seconds=5)

# Get messages with a specific consumer ID
messages = queue.get_messages(count=5, consumer_id="worker-123")

# Process the messages
for message in messages:
    print(f"Message ID: {message.id}")
    print(f"Data: {message.data}")
    
    # Process the message...
    
    # Acknowledge successful processing
    queue.acknowledge_messages([message.id])
```

#### `acknowledge_messages`

```python
acknowledge_messages(message_ids: List[str]) -> int
```

Acknowledge messages as processed without removing them from the stream.

**Parameters**:
- `message_ids` (List[str]): List of message IDs to acknowledge

**Returns**: Number of messages acknowledged

**Example**:
```python
# Get messages
messages = queue.get_messages(count=5)

# Process them
for message in messages:
    # Process the message...
    pass

# Acknowledge all messages at once
acknowledged = queue.acknowledge_messages([m.id for m in messages])
print(f"Acknowledged {acknowledged} messages")
```

#### `delete_messages`

```python
delete_messages(message_ids: List[str]) -> int
```

Permanently delete messages from the queue.

**Parameters**:
- `message_ids` (List[str]): List of message IDs to delete

**Returns**: Number of messages deleted

**Example**:
```python
# Delete specific messages
deleted = queue.delete_messages(["1615456789012-0", "1615456789013-0"])
print(f"Deleted {deleted} messages")

# Get messages and then delete them after processing
messages = queue.get_messages(count=5)
for message in messages:
    # Process the message...
    pass

# Delete all processed messages
queue.delete_messages([m.id for m in messages])
```

#### `move_to_dlq`

```python
move_to_dlq(
    message_ids: List[str],
    reason: str,
    dlq: Optional["Queue"] = None
) -> int
```

Move messages to the dead letter queue.

**Parameters**:
- `message_ids` (List[str]): List of message IDs to move
- `reason` (str): Reason for moving to DLQ
- `dlq` (Optional[Queue]): Dead letter queue to move to

**Returns**: Number of messages moved

**Example**:
```python
# Get the DLQ
dlq = mq.get_dead_letter_queue("myqueue")

# Move specific messages to the DLQ
moved = queue.move_to_dlq(
    ["1615456789012-0", "1615456789013-0"],
    "Failed processing: Invalid format",
    dlq
)
print(f"Moved {moved} messages to DLQ")

# Error handling during message processing
messages = queue.get_messages(count=5)
for message in messages:
    try:
        # Process the message...
        process_message(message.data)
        
        # Acknowledge success
        queue.acknowledge_messages([message.id])
    except Exception as e:
        # Move to DLQ on failure
        queue.move_to_dlq([message.id], f"Processing error: {e}", dlq)
```

#### `requeue_messages`

```python
requeue_messages(
    message_ids: List[str],
    destination_queue: Optional["Queue"] = None
) -> int
```

Move messages from a DLQ back to their original queue for reprocessing.

**Parameters**:
- `message_ids` (List[str]): List of message IDs to requeue
- `destination_queue` (Optional[Queue]): Queue to move messages to

**Returns**: Number of messages requeued

**Example**:
```python
# Get messages from DLQ
failed_messages = dlq.get_messages(count=10)

# Get the original queue
main_queue = mq.get_queue("myqueue")

# Requeue the messages
requeued = dlq.requeue_messages(
    [message.id for message in failed_messages],
    main_queue
)
print(f"Requeued {requeued} messages for reprocessing")
```

#### `purge`

```python
purge() -> int
```

Purge all messages from the queue.

**Returns**: Number of messages purged

**Example**:
```python
# Remove all messages from the queue
purged = queue.purge()
print(f"Purged {purged} messages from the queue")
```

#### `get_info`

```python
get_info() -> QueueInfo
```

Get information about the queue.

**Returns**: QueueInfo object with queue information

**Example**:
```python
# Get queue information
queue_info = queue.get_info()
print(f"Queue: {queue_info.name}")
print(f"Is DLQ: {queue_info.is_dlq}")
print(f"Message count: {queue_info.message_count}")
print(f"Consumer group: {queue_info.consumer_group}")
print(f"Pending messages: {queue_info.pending_messages}")
print(f"Created at: {queue_info.created_at}")
```

## QueueInfo Class

The `QueueInfo` class provides information about a queue.

### Attributes

- `name` (str): Name of the queue
- `is_dlq` (bool): Whether this queue is a dead letter queue
- `message_count` (int): Number of messages in the queue
- `consumer_group` (Optional[str]): Name of the consumer group
- `pending_messages` (int): Number of pending messages
- `created_at` (Optional[float]): Timestamp when queue was created

### Methods

The `QueueInfo` class is primarily a data class and does not have significant methods beyond basic object functionality.

## Example Usage

```python
from leanmq import LeanMQ

# Initialize LeanMQ
mq = LeanMQ(redis_host="localhost", redis_port=6379)

# Create a queue pair
main_queue, dlq = mq.create_queue_pair("notifications")

# Send messages
for i in range(5):
    main_queue.send_message({
        "id": i,
        "message": f"Notification {i}",
        "timestamp": time.time()
    })

# Get and process messages
messages = main_queue.get_messages(count=10)
for message in messages:
    print(f"Processing message: {message.data}")
    
    try:
        # Process the message
        process_notification(message.data)
        
        # Acknowledge success
        main_queue.acknowledge_messages([message.id])
    except Exception as e:
        print(f"Error processing message: {e}")
        # Move to DLQ
        main_queue.move_to_dlq([message.id], f"Processing error: {e}", dlq)

# Get queue information
queue_info = main_queue.get_info()
print(f"Queue: {queue_info.name}")
print(f"Message count: {queue_info.message_count}")

# Reprocess failed messages from DLQ
failed_messages = dlq.get_messages(count=10)
if failed_messages:
    # Fix the issue that caused the failure
    fix_processing_issue()
    
    # Requeue the messages
    dlq.requeue_messages([m.id for m in failed_messages], main_queue)
```

## Related

- [Core API](./core.md): Documentation for the LeanMQ class that creates and manages queues
- [Message API](./message.md): Documentation for the Message class returned by `get_messages()`
