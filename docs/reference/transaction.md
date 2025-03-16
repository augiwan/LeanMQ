# Transaction API Reference

This reference documents the Transaction class and related functionality in LeanMQ.

## Transaction Class

The `Transaction` class represents a Redis transaction for atomic operations. It allows you to group multiple message send operations into a single atomic unit that either all succeed or all fail together.

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

Add a message send operation to the transaction.

**Parameters**:
- `queue` (Queue): Queue to send the message to
- `data` (Dict[str, Any]): Message data
- `ttl_seconds` (Optional[int]): Time-to-live for the message in seconds

**Example**:
```python
with mq.transaction() as tx:
    tx.send_message(queue1, {"key": "value1"})
    tx.send_message(queue2, {"key": "value2"}, ttl_seconds=3600)
```

#### `_execute`

```python
_execute() -> None
```

Execute the transaction.

::: warning
This method is called automatically when the context manager exits. You should not call it directly.
:::

## Using Transactions

### Starting a Transaction

Transactions are typically used with a context manager:

```python
from leanmq import LeanMQ

# Initialize LeanMQ
mq = LeanMQ(redis_host="localhost", redis_port=6379)

# Create queues
order_queue, _ = mq.create_queue_pair("orders")
notification_queue, _ = mq.create_queue_pair("notifications")
audit_queue, _ = mq.create_queue_pair("audit")

# Start a transaction
with mq.transaction() as tx:
    # Add operations to the transaction
    tx.send_message(order_queue, {
        "order_id": "ORD-12345",
        "status": "paid",
        "amount": 99.99
    })
    
    tx.send_message(notification_queue, {
        "type": "order_paid",
        "order_id": "ORD-12345",
        "message": "Payment received for order ORD-12345"
    })
    
    tx.send_message(audit_queue, {
        "action": "order_payment",
        "order_id": "ORD-12345",
        "amount": 99.99,
        "timestamp": time.time()
    })
    
    # The transaction is automatically executed when exiting the context
```

### Error Handling

If any operation in the transaction fails, the entire transaction is rolled back:

```python
from leanmq import LeanMQ, TransactionError

mq = LeanMQ(redis_host="localhost", redis_port=6379)
queue1, _ = mq.create_queue_pair("queue1")
queue2, _ = mq.create_queue_pair("queue2")

try:
    with mq.transaction() as tx:
        tx.send_message(queue1, {"key": "value1"})
        
        # Simulate an error condition
        if some_error_condition:
            raise ValueError("Something went wrong")
            
        tx.send_message(queue2, {"key": "value2"})
        
except (TransactionError, ValueError) as e:
    print(f"Transaction failed: {e}")
    # Handle the failure (e.g., retry or notify)
```

### Manual Transaction Handling

If you need more control over when the transaction is executed, you can avoid using the context manager:

```python
# Create a transaction
tx = mq.transaction()

# Add operations
tx.send_message(queue1, {"key": "value1"})
tx.send_message(queue2, {"key": "value2"})

try:
    # Execute the transaction manually
    tx._execute()
except TransactionError as e:
    print(f"Transaction failed: {e}")
```

However, using the context manager is recommended as it ensures proper cleanup even if exceptions occur.

## Transaction Patterns

### Multi-Queue Publishing

Use transactions to ensure messages are published to multiple queues atomically:

```python
def publish_event(event_type, event_data):
    """Publish an event to multiple queues atomically."""
    with mq.transaction() as tx:
        # Add event timestamp
        event_data["timestamp"] = time.time()
        
        # Publish to main event queue
        tx.send_message(event_queue, {
            "type": event_type,
            "data": event_data
        })
        
        # Publish to specific event type queue
        type_specific_queue = mq.get_queue(f"events:{event_type}")
        if type_specific_queue:
            tx.send_message(type_specific_queue, event_data)
        
        # Add to analytics queue
        tx.send_message(analytics_queue, {
            "event_type": event_type,
            "event_data": event_data,
            "source": "event_service"
        })
```

### Event Sourcing

Use transactions to implement event sourcing patterns:

```python
def update_user_profile(user_id, updates):
    """Update user profile and publish events atomically."""
    with mq.transaction() as tx:
        # Create the event
        event = {
            "user_id": user_id,
            "changes": updates,
            "timestamp": time.time()
        }
        
        # Publish to user events stream
        tx.send_message(user_events_queue, {
            "type": "user_profile_updated",
            "data": event
        })
        
        # Publish to each interested service's queue
        if "email" in updates:
            tx.send_message(email_service_queue, {
                "action": "update_email",
                "user_id": user_id,
                "new_email": updates["email"]
            })
            
        if "preferences" in updates:
            tx.send_message(preferences_service_queue, {
                "action": "update_preferences",
                "user_id": user_id,
                "preferences": updates["preferences"]
            })
```

### Workflow Steps

Use transactions to implement workflow steps:

```python
def complete_order_step(order_id, step, result):
    """Complete a step in an order processing workflow."""
    with mq.transaction() as tx:
        # Log the step completion
        tx.send_message(workflow_log_queue, {
            "order_id": order_id,
            "step": step,
            "result": result,
            "timestamp": time.time()
        })
        
        # Determine the next step
        if step == "payment_processing":
            if result["status"] == "success":
                # Trigger fulfillment
                tx.send_message(fulfillment_queue, {
                    "order_id": order_id,
                    "action": "start_fulfillment",
                    "payment_info": result["payment_info"]
                })
            else:
                # Payment failed, trigger notification
                tx.send_message(notification_queue, {
                    "type": "payment_failed",
                    "order_id": order_id,
                    "reason": result["reason"]
                })
```

## Transaction Limitations

It's important to understand the limitations of transactions in LeanMQ:

1. **Redis-Only Operations**: Transactions only encompass Redis operations. If your transaction needs to involve other systems (databases, APIs, etc.), you'll need to implement your own two-phase commit pattern.

2. **No Read Operations**: Redis transactions don't support reading values during the transaction and making decisions based on those values.

3. **No Rollback for Queue Creation**: Creating queues is not part of the transaction and cannot be rolled back.

4. **Network Failures**: If a network failure occurs after operations are queued but before the transaction is executed, the transaction will fail without being executed.

5. **Limited Error Reporting**: If a transaction fails, you get a generic TransactionError without detailed information about which specific operation failed.

## Best Practices

### Keep Transactions Focused

Each transaction should encompass a single logical operation. Avoid mixing unrelated operations in the same transaction.

### Pre-Create Queues

Create all necessary queues before starting your transactions to avoid partial failures:

```python
# Good practice - create queues first
queue1, _ = mq.create_queue_pair("queue1")
queue2, _ = mq.create_queue_pair("queue2")

with mq.transaction() as tx:
    tx.send_message(queue1, {"key": "value1"})
    tx.send_message(queue2, {"key": "value2"})
```

### Implement Retry Logic

For critical operations, implement proper retry logic:

```python
def send_with_retry(max_retries=3, backoff_factor=2):
    """Send messages with retry logic."""
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            with mq.transaction() as tx:
                tx.send_message(queue1, {"key": "value1"})
                tx.send_message(queue2, {"key": "value2"})
            # Success, exit the loop
            return True
        except TransactionError as e:
            retries += 1
            last_error = e
            wait_time = backoff_factor ** retries
            print(f"Transaction failed (attempt {retries}/{max_retries}), "
                  f"retrying in {wait_time} seconds: {e}")
            time.sleep(wait_time)
    
    # All retries failed
    print(f"All {max_retries} transaction attempts failed: {last_error}")
    return False
```

### Design for Idempotency

Make sure your message handlers are idempotent (can be safely repeated):

```python
def handle_order_payment(data):
    """Handle order payment message (idempotent implementation)."""
    order_id = data["order_id"]
    payment_id = data["payment_id"]
    
    # Check if this payment was already processed
    if db.payment_exists(payment_id):
        print(f"Payment {payment_id} already processed, ignoring duplicate")
        return
    
    # Process the payment
    result = process_payment(order_id, data["amount"])
    
    # Record the payment to prevent duplicates
    db.record_payment(payment_id, order_id, result)
```

## Related

- [Core API](./core.md): Documentation for the LeanMQ class that creates transactions
- [Queue API](./queue.md): Documentation for the Queue class used in transactions
- [Transactions Guide](../guide/advanced/transactions.md): Detailed guide to using transactions effectively
