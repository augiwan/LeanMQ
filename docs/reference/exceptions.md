# Exceptions API Reference

This reference documents the exception classes in LeanMQ.

## Exception Hierarchy

LeanMQ uses a hierarchy of exception classes to represent different types of errors:

```
LeanMQError
├── ConnectionError
├── QueueError
│   ├── QueueNotFoundError
│   └── DeadLetterQueueNotFoundError
├── MessageError
└── TransactionError
```

## Base Exception

### `LeanMQError`

Base exception for all LeanMQ errors.

```python
class LeanMQError(Exception):
    """Base exception for all LeanMQ errors."""
    pass
```

This is the parent class for all other exceptions in LeanMQ. You can catch this exception type to handle any LeanMQ-related error:

```python
try:
    # LeanMQ operations
    queue = mq.get_queue("non_existent_queue")
    if queue:
        queue.send_message({"key": "value"})
except LeanMQError as e:
    print(f"LeanMQ operation failed: {e}")
```

## Connection Exceptions

### `ConnectionError`

Raised when there is an error connecting to Redis.

```python
class ConnectionError(LeanMQError):
    """Raised when there is an error connecting to Redis."""
    pass
```

This exception is raised when LeanMQ cannot connect to the Redis server:

```python
try:
    # Initialize with incorrect Redis connection details
    mq = LeanMQ(redis_host="wrong-host", redis_port=1234)
    queue, _ = mq.create_queue_pair("myqueue")
except ConnectionError as e:
    print(f"Cannot connect to Redis: {e}")
    # Attempt fallback or notify administrator
```

## Queue Exceptions

### `QueueError`

Raised when there is an error with a queue operation.

```python
class QueueError(LeanMQError):
    """Raised when there is an error with a queue operation."""
    pass
```

This is the parent class for more specific queue-related exceptions:

```python
try:
    # Queue operations
    queue.purge()
except QueueError as e:
    print(f"Queue operation failed: {e}")
```

### `QueueNotFoundError`

Raised when a queue cannot be found.

```python
class QueueNotFoundError(QueueError):
    """Raised when a queue cannot be found."""
    pass
```

This exception is raised when trying to access a queue that doesn't exist:

```python
try:
    # Try to get a non-existent queue
    queue = mq.get_queue("non_existent_queue")
    if queue is None:
        raise QueueNotFoundError(f"Queue 'non_existent_queue' not found")
    # Proceed with queue operations
    queue.send_message({"key": "value"})
except QueueNotFoundError as e:
    print(f"Queue not found: {e}")
    # Create the queue or handle the error
```

### `DeadLetterQueueNotFoundError`

Raised when a dead letter queue cannot be found.

```python
class DeadLetterQueueNotFoundError(QueueError):
    """Raised when a dead letter queue cannot be found."""
    pass
```

This exception is raised when trying to access a dead letter queue that doesn't exist:

```python
try:
    # Try to get the DLQ for a queue
    dlq = mq.get_dead_letter_queue("myqueue")
    if dlq is None:
        raise DeadLetterQueueNotFoundError(f"DLQ for 'myqueue' not found")
    # Proceed with DLQ operations
    failed_messages = dlq.get_messages(count=10)
except DeadLetterQueueNotFoundError as e:
    print(f"DLQ not found: {e}")
    # Create the DLQ or handle the error
```

## Message Exceptions

### `MessageError`

Raised when there is an error processing a message.

```python
class MessageError(LeanMQError):
    """Raised when there is an error processing a message."""
    pass
```

This exception is raised for message-related errors:

```python
try:
    # Get messages from the queue
    messages = queue.get_messages(count=10)
    
    # Process the messages
    for message in messages:
        if not validate_message(message.data):
            raise MessageError(f"Invalid message format: {message.id}")
        
        process_message(message.data)
        queue.acknowledge_messages([message.id])
except MessageError as e:
    print(f"Message processing error: {e}")
    # Handle the error (e.g., move to DLQ)
```

## Transaction Exceptions

### `TransactionError`

Raised when there is an error in a transaction.

```python
class TransactionError(LeanMQError):
    """Raised when there is an error in a transaction."""
    pass
```

This exception is raised when a transaction fails:

```python
try:
    # Start a transaction
    with mq.transaction() as tx:
        tx.send_message(queue1, {"key": "value1"})
        tx.send_message(queue2, {"key": "value2"})
        # If anything goes wrong, TransactionError will be raised
except TransactionError as e:
    print(f"Transaction failed: {e}")
    # Implement retry logic or fallback
```

## Error Handling Strategies

### Basic Error Handling

For basic applications, you can catch specific exceptions based on the operation:

```python
try:
    # Initialize LeanMQ
    mq = LeanMQ(redis_host="localhost", redis_port=6379)
    
    # Create and use queues
    main_queue, dlq = mq.create_queue_pair("myqueue")
    main_queue.send_message({"key": "value"})
    
    # Process messages
    messages = main_queue.get_messages(count=10)
    for message in messages:
        process_message(message.data)
        main_queue.acknowledge_messages([message.id])
        
except ConnectionError as e:
    print(f"Redis connection error: {e}")
    # Retry connection or exit
    
except QueueError as e:
    print(f"Queue operation error: {e}")
    # Handle queue errors
    
except MessageError as e:
    print(f"Message processing error: {e}")
    # Handle message errors
    
except LeanMQError as e:
    print(f"Unexpected LeanMQ error: {e}")
    # Handle any other LeanMQ errors
    
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle non-LeanMQ errors
```

### Advanced Error Handling with Retries

For production applications, implement retry logic with backoff:

```python
def with_retries(operation, max_retries=3, initial_delay=1, backoff_factor=2):
    """Execute an operation with retry logic."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Execute the operation
            return operation()
        except ConnectionError as e:
            # Connection errors might resolve with time
            last_exception = e
            
            # Calculate delay with exponential backoff
            delay = initial_delay * (backoff_factor ** attempt)
            
            print(f"Connection error (attempt {attempt+1}/{max_retries}): {e}")
            print(f"Retrying in {delay} seconds...")
            
            time.sleep(delay)
        except (QueueNotFoundError, DeadLetterQueueNotFoundError) as e:
            # Queue not found - fatal error, don't retry
            print(f"Queue not found: {e}")
            raise
        except LeanMQError as e:
            # Other LeanMQ errors might be transient
            last_exception = e
            
            # Calculate delay with exponential backoff
            delay = initial_delay * (backoff_factor ** attempt)
            
            print(f"LeanMQ error (attempt {attempt+1}/{max_retries}): {e}")
            print(f"Retrying in {delay} seconds...")
            
            time.sleep(delay)
    
    # All retries failed
    raise last_exception or RuntimeError("Operation failed with no specific error")

# Example usage
try:
    # Execute operation with retries
    result = with_retries(
        lambda: mq.get_queue("myqueue").send_message({"key": "value"})
    )
    print(f"Message sent with ID: {result}")
except Exception as e:
    print(f"All retries failed: {e}")
```

### Error Monitoring and Alerting

For production systems, implement monitoring for LeanMQ exceptions:

```python
def monitor_exception(exception, context=None):
    """Monitor exceptions for alerts and metrics."""
    exception_type = type(exception).__name__
    exception_message = str(exception)
    
    # Log the exception
    logger.error(
        f"LeanMQ Exception: {exception_type}: {exception_message}",
        extra={"context": context or {}}
    )
    
    # Track metrics (e.g., using Prometheus, Datadog, etc.)
    metrics.increment(
        "leanmq_errors",
        tags={
            "type": exception_type,
            "queue": context.get("queue_name") if context else "unknown"
        }
    )
    
    # Send alerts for critical exceptions
    if isinstance(exception, ConnectionError):
        alerts.send_alert(
            "LeanMQ Redis Connection Failure",
            f"Connection to Redis failed: {exception_message}",
            severity="critical"
        )
    elif isinstance(exception, TransactionError):
        alerts.send_alert(
            "LeanMQ Transaction Failure",
            f"Transaction failed: {exception_message}",
            severity="high"
        )

# Example usage
try:
    # LeanMQ operations
    queue = mq.get_queue("myqueue")
    queue.send_message({"key": "value"})
except LeanMQError as e:
    monitor_exception(e, context={"queue_name": "myqueue", "operation": "send_message"})
    # Handle the error
```

## Related

- [Core API](./core.md): Documentation for the LeanMQ class that may raise these exceptions
- [Queue API](./queue.md): Documentation for the Queue class that may raise these exceptions
- [Transaction API](./transaction.md): Documentation for the Transaction class that may raise TransactionError
