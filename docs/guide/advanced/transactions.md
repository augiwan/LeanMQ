# Transactions in LeanMQ

This guide explains how to use transactions in LeanMQ to ensure atomic operations across multiple queues. Transactions are essential when you need to guarantee that multiple message operations either all succeed or all fail together.

## Understanding Transactions

In distributed systems, ensuring consistency across multiple operations is challenging. LeanMQ's transaction support provides a way to group operations and execute them atomically, using Redis's built-in transaction mechanism.

Key benefits of using transactions:
- **Atomicity**: All operations succeed or none do
- **Consistency**: No partial updates that could leave your system in an invalid state
- **Isolation**: Other operations don't see the intermediate state

## When to Use Transactions

Transactions are valuable in several scenarios:

1. **Cross-service coordination**:
   When an event needs to trigger notifications to multiple services

2. **Data synchronization**:
   When updating multiple data stores that need to stay in sync

3. **Multi-step workflows**:
   When a process involves several sequential steps that must be treated as a unit

4. **Audit and history tracking**:
   When you need to record actions in both a primary queue and an audit queue

## Basic Transaction Usage

Here's how to use transactions in LeanMQ:

```python
from leanmq import LeanMQ

# Initialize LeanMQ
mq = LeanMQ(redis_host="localhost", redis_port=6379)

# Create queues
order_queue, _ = mq.create_queue_pair("orders")
notification_queue, _ = mq.create_queue_pair("notifications")
audit_queue, _ = mq.create_queue_pair("audit")

# Using a transaction with context manager (recommended)
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

When the context manager exits, all queued operations are executed atomically. If any operation fails, the entire transaction is rolled back.

## Handling Transaction Errors

Transactions can fail for various reasons:

```python
from leanmq import TransactionError

try:
    with mq.transaction() as tx:
        tx.send_message(order_queue, {"order_id": "ORD-12345", "status": "shipped"})
        tx.send_message(notification_queue, {"type": "order_shipped", "order_id": "ORD-12345"})
except TransactionError as e:
    print(f"Transaction failed: {e}")
    # Implement fallback logic or retry
```

Common causes of transaction failures:
- Redis server errors
- Connection issues
- Validation failures

## Transaction Limitations

It's important to understand the limitations of transactions in LeanMQ:

1. **No rollback for queue creation**:
   Creating queues is not part of the transaction and cannot be rolled back

2. **No automatic retries**:
   LeanMQ doesn't automatically retry failed transactions; you need to implement retry logic

3. **No distributed transactions**:
   Transactions only work within a single Redis instance

4. **Read operations**:
   Transactions don't include read operations, only writes

## Advanced Transaction Patterns

### Saga Pattern

For complex, multi-step processes, you can implement the Saga pattern using LeanMQ:

```python
def process_order(order_id):
    try:
        # Step 1: Payment processing
        with mq.transaction() as tx:
            tx.send_message(payment_queue, {"order_id": order_id, "action": "process_payment"})
            tx.send_message(audit_queue, {"order_id": order_id, "step": "payment_initiated"})
        
        # Step 2: Inventory allocation
        with mq.transaction() as tx:
            tx.send_message(inventory_queue, {"order_id": order_id, "action": "allocate_inventory"})
            tx.send_message(audit_queue, {"order_id": order_id, "step": "inventory_allocated"})
        
        # Step 3: Shipping
        with mq.transaction() as tx:
            tx.send_message(shipping_queue, {"order_id": order_id, "action": "create_shipment"})
            tx.send_message(audit_queue, {"order_id": order_id, "step": "shipping_initiated"})
            
    except Exception as e:
        # Send compensating transactions for rollback
        with mq.transaction() as tx:
            tx.send_message(compensation_queue, {
                "order_id": order_id,
                "error": str(e),
                "timestamp": time.time()
            })
```

This approach breaks down a complex process into smaller atomic transactions, with compensating transactions for rollback.

### Outbox Pattern

The outbox pattern is useful for reliably publishing events from a service:

```python
def update_user(user_id, user_data):
    # First, update the user in your database
    db.update_user(user_id, user_data)
    
    # Then, use a transaction to ensure all events are published
    with mq.transaction() as tx:
        # Send to internal services
        tx.send_message(user_update_queue, {
            "type": "user_updated",
            "user_id": user_id,
            "changes": user_data
        })
        
        # Send to external webhook service
        tx.send_message(webhook_queue, {
            "destination": "https://partner-api.example.com/webhooks",
            "payload": {
                "event": "user.updated",
                "user_id": user_id,
                "timestamp": time.time()
            }
        })
        
        # Send to analytics
        tx.send_message(analytics_queue, {
            "event": "user_updated",
            "user_id": user_id,
            "properties": {
                "changed_fields": list(user_data.keys())
            }
        })
```

This ensures that either all events are published or none are, maintaining consistency.

### Two-Phase Operations

For operations requiring confirmation, you can implement a two-phase approach:

```python
# Phase 1: Prepare
def prepare_order_cancellation(order_id):
    with mq.transaction() as tx:
        tx.send_message(order_queue, {
            "type": "cancellation_prepared",
            "order_id": order_id,
            "timestamp": time.time()
        })
        
        tx.send_message(preparation_queue, {
            "action": "prepare_cancellation",
            "order_id": order_id,
            "services": ["payment", "inventory", "shipping"]
        })

# Phase 2: Commit (after all services have confirmed)
def commit_order_cancellation(order_id):
    with mq.transaction() as tx:
        tx.send_message(order_queue, {
            "type": "cancellation_committed",
            "order_id": order_id,
            "timestamp": time.time()
        })
        
        tx.send_message(commit_queue, {
            "action": "commit_cancellation",
            "order_id": order_id,
            "services": ["payment", "inventory", "shipping"]
        })
```

This pattern is useful when you need to ensure all services can perform an operation before committing to it.

## Best Practices

### Keep Transactions Focused

Limit each transaction to a single logical operation:

```python
# Good - focused transaction
with mq.transaction() as tx:
    tx.send_message(order_queue, {"order_id": "123", "status": "shipped"})
    tx.send_message(notification_queue, {"type": "order_shipped", "order_id": "123"})

# Bad - mixing unrelated operations
with mq.transaction() as tx:
    tx.send_message(order_queue, {"order_id": "123", "status": "shipped"})
    tx.send_message(user_queue, {"user_id": "456", "action": "update_profile"})
    tx.send_message(product_queue, {"product_id": "789", "action": "update_stock"})
```

### Avoid Long-Running Transactions

Keep transactions brief to avoid holding Redis resources:

```python
# Bad - performing slow operations within transaction context
with mq.transaction() as tx:
    # Don't do this! Slow external API call
    api_result = requests.get("https://slow-api.example.com/data")
    
    tx.send_message(result_queue, {"result": api_result.json()})

# Good - prepare everything before starting the transaction
api_result = requests.get("https://slow-api.example.com/data")

with mq.transaction() as tx:
    tx.send_message(result_queue, {"result": api_result.json()})
```

### Implement Proper Error Handling

Always handle transaction errors gracefully:

```python
def send_with_retry(max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            with mq.transaction() as tx:
                tx.send_message(queue1, {"key": "value1"})
                tx.send_message(queue2, {"key": "value2"})
            # Success, exit the loop
            return True
        except TransactionError as e:
            retries += 1
            print(f"Transaction failed (attempt {retries}/{max_retries}): {e}")
            # Exponential backoff
            time.sleep(2 ** retries)
    
    # If we get here, all retries failed
    print("All transaction attempts failed")
    return False
```

### Use Idempotent Operations

Design your message handlers to be idempotent (can be safely repeated):

```python
@webhook.get("/order/status/")
def handle_order_status(data):
    order_id = data.get("order_id")
    new_status = data.get("status")
    
    # Check if this exact update has already been processed
    current_status = db.get_order_status(order_id)
    if current_status == new_status:
        print(f"Order {order_id} already has status {new_status}, skipping")
        return
    
    # Process the status update
    db.update_order_status(order_id, new_status)
```

This ensures that if a message is processed multiple times (due to retries or redelivery), it won't cause issues.

## Debugging Transactions

When troubleshooting transaction issues:

1. **Enable verbose logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Monitor Redis directly**:
   Use Redis CLI or a monitoring tool to observe what's happening:
   ```bash
   redis-cli monitor
   ```

3. **Use incremental testing**:
   Test each operation individually before combining them in a transaction.

## Performance Considerations

Transactions in Redis have some performance implications:

- **Blocking**: Redis transactions block the server for their duration
- **No intermediate results**: You can't make decisions based on intermediate operations
- **Single-threaded**: Redis executes transactions on a single thread

For high-volume applications, consider:

- Keeping transactions small
- Distributing transactions across different Redis instances
- Using Redis Cluster for horizontal scaling

## Next Steps

Now that you understand how to use transactions in LeanMQ, you can:

- Explore [error handling strategies](./error-handling.md)
- Learn about [scaling LeanMQ](./scaling.md) for high-volume applications
- See [production deployment best practices](./production.md)

For complete API details, visit the [Transaction API reference](../../reference/transaction.md).
