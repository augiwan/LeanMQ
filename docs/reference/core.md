# Core API Reference

This reference documents the core classes and methods in LeanMQ.

## LeanMQ Class

The `LeanMQ` class is the main entry point for the LeanMQ library, providing methods for creating queues, sending messages, and managing transactions.

### Constructor

```python
LeanMQ(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
    prefix: str = "",
    connection_timeout: int = 5,
    max_retries: int = 3,
    retry_interval: int = 1
)
```

**Parameters**:
- `redis_host` (str): Redis server hostname
- `redis_port` (int): Redis server port
- `redis_db` (int): Redis database number
- `redis_password` (Optional[str]): Redis password, if required
- `prefix` (str): Prefix for queue names
- `connection_timeout` (int): Timeout for Redis connections in seconds
- `max_retries` (int): Maximum number of connection retries
- `retry_interval` (int): Interval between retries in seconds

**Returns**: A new LeanMQ instance

### Methods

#### `create_queue_pair`

```python
create_queue_pair(
    queue_name: str,
    create_consumer_group: bool = True
) -> Tuple[Queue, Queue]
```

Creates a queue and its corresponding dead letter queue.

**Parameters**:
- `queue_name` (str): Name of the queue to create
- `create_consumer_group` (bool): Whether to create a consumer group for the queue

**Returns**: A tuple containing (main_queue, dead_letter_queue)

#### `get_queue`

```python
get_queue(queue_name: str) -> Optional[Queue]
```

Gets a queue object for the specified queue name.

**Parameters**:
- `queue_name` (str): Name of the queue to get

**Returns**: Queue object if the queue exists, None otherwise

#### `get_dead_letter_queue`

```python
get_dead_letter_queue(queue_name: str) -> Optional[Queue]
```

Gets the dead letter queue for the specified queue name.

**Parameters**:
- `queue_name` (str): Name of the main queue

**Returns**: Queue object for the DLQ if it exists, None otherwise

#### `list_queues`

```python
list_queues() -> List[QueueInfo]
```

Lists all queues managed by this LeanMQ instance.

**Returns**: List of QueueInfo objects with queue information

#### `delete_queue`

```python
delete_queue(queue_name: str, delete_dlq: bool = False) -> bool
```

Deletes a queue and optionally its dead letter queue.

**Parameters**:
- `queue_name` (str): Name of the queue to delete
- `delete_dlq` (bool): Whether to also delete the associated dead letter queue

**Returns**: True if the queue was deleted, False otherwise

#### `process_expired_messages`

```python
process_expired_messages() -> int
```

Processes expired messages (those with TTL) across all queues.

**Returns**: Number of expired messages processed

#### `transaction`

```python
transaction() -> Transaction
```

Starts a transaction for atomic operations.

**Returns**: A Transaction object that can be used with a context manager

#### `close`

```python
close() -> None
```

Closes Redis connections.

### Context Manager Support

The `LeanMQ` class supports the context manager protocol:

```python
with LeanMQ(redis_host="localhost") as mq:
    # Use mq here
    queue, _ = mq.create_queue_pair("myqueue")
    # ...
# Redis connections are automatically closed when exiting the context
```

## Transaction Class

The `Transaction` class represents a Redis transaction for atomic operations.

### Constructor

```python
Transaction(redis_connection: Redis)
```

**Parameters**:
- `redis_connection` (Redis): Redis connection to use for the transaction

::: warning
You should not create Transaction objects directly. Instead, use the `transaction()` method of the LeanMQ class.
:::

### Methods

#### `send_message`

```python
send_message(
    queue: Queue,
    data: Dict[str, Any],
    ttl_seconds: Optional[int] = None
) -> None
```

Adds a message send operation to the transaction.

**Parameters**:
- `queue` (Queue): Queue to send the message to
- `data` (Dict[str, Any]): Message data
- `ttl_seconds` (Optional[int]): Time-to-live for the message in seconds

### Context Manager Support

The `Transaction` class is designed to be used with a context manager:

```python
with mq.transaction() as tx:
    tx.send_message(queue1, {"key": "value1"})
    tx.send_message(queue2, {"key": "value2"})
# Transaction is executed when exiting the context
```

## Example Usage

```python
from leanmq import LeanMQ

# Initialize LeanMQ
mq = LeanMQ(
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    prefix="myapp:"
)

# Create a queue pair
main_queue, dlq = mq.create_queue_pair("notifications")

# Send a message
message_id = main_queue.send_message({"user_id": 123, "message": "Hello, world!"})
print(f"Sent message with ID: {message_id}")

# Start a transaction
with mq.transaction() as tx:
    # Add operations to the transaction
    tx.send_message(main_queue, {"user_id": 456, "message": "Transaction message 1"})
    tx.send_message(main_queue, {"user_id": 789, "message": "Transaction message 2"})
    # Transaction is automatically executed when exiting the context

# Get messages from the queue
messages = main_queue.get_messages(count=10)
for message in messages:
    print(f"Received message: {message.data}")
    main_queue.acknowledge_messages([message.id])

# Close connections when done
mq.close()
```

## Related

- [Queue API](./queue.md): Documentation for the Queue class and related methods
- [Message API](./message.md): Documentation for the Message class
- [Transaction API](./transaction.md): Detailed documentation for transactions
