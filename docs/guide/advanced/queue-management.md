# Advanced Queue Management

This guide covers advanced queue management techniques in LeanMQ, including dead letter queues, message TTL, queue monitoring, and cleanup strategies.

## Queue Lifecycle

In LeanMQ, queues are created on demand when you first use them, and they persist in Redis until explicitly deleted. Understanding the queue lifecycle helps you manage your application effectively.

### Creating Queues

The recommended way to create queues is using the `create_queue_pair` method, which creates both the main queue and its corresponding dead letter queue:

```python
from leanmq import LeanMQ

mq = LeanMQ(redis_host="localhost", redis_port=6379)

# Create a main queue and its DLQ
main_queue, dlq = mq.create_queue_pair("orders")
```

Behind the scenes, this creates:
- A main queue named `orders`
- A dead letter queue named `orders:dlq`
- A consumer group for the main queue

### Queue Naming Conventions

LeanMQ uses a simple naming convention for queues:

- Main queues have the name you provide (e.g., `orders`)
- Dead letter queues have `:dlq` appended (e.g., `orders:dlq`)
- The prefix you provide when initializing LeanMQ is added to all queue names

For example, with a prefix of `myapp:`:
- Main queue: `myapp:orders`
- DLQ: `myapp:orders:dlq`

This helps keep your queues organized, especially when sharing a Redis instance with other applications.

### Listing Queues

To see all queues managed by LeanMQ:

```python
queues = mq.list_queues()
for queue_info in queues:
    print(f"Queue: {queue_info.name}")
    print(f"  Is DLQ: {queue_info.is_dlq}")
    print(f"  Message count: {queue_info.message_count}")
    print(f"  Pending messages: {queue_info.pending_messages}")
    print(f"  Created at: {queue_info.created_at}")
    print("---")
```

### Deleting Queues

When a queue is no longer needed, you can delete it:

```python
# Delete a queue and its DLQ
mq.delete_queue("orders", delete_dlq=True)

# Delete just the main queue, keeping the DLQ
mq.delete_queue("orders", delete_dlq=False)
```

## Dead Letter Queues (DLQs)

Dead letter queues are a critical feature for reliable message processing. They store messages that couldn't be processed successfully, allowing you to:

- Inspect failed messages
- Debug processing errors
- Reprocess messages after fixing issues
- Prevent poison messages from blocking your main queue

### When Messages Move to DLQ

Messages are moved to the DLQ in these scenarios:

1. When explicitly moved using `move_to_dlq()`
2. When the webhook handler raises an exception
3. When a message exceeds its maximum delivery attempts (if implemented in your code)

### Working with DLQs

Here's how to interact with DLQs:

```python
# Get the DLQ for a queue
dlq = mq.get_dead_letter_queue("orders")

# Get failed messages from the DLQ
failed_messages = dlq.get_messages(count=10)

for message in failed_messages:
    print(f"Message ID: {message.id}")
    print(f"Data: {message.data}")
    print(f"Timestamp: {message.timestamp}")
    print(f"Delivery attempts: {message.delivery_count}")
    
    # Process or inspect the message
    try:
        # Try to fix or manually process the message
        fixed = fix_message_issue(message.data)
        if fixed:
            # Acknowledge this message in the DLQ
            dlq.acknowledge_messages([message.id])
    except Exception as e:
        print(f"Still can't process message: {e}")
```

### Requeuing Failed Messages

After fixing the issue that caused messages to fail, you can requeue them to the main queue:

```python
# Get messages from DLQ
failed_messages = dlq.get_messages(count=10)

# Get message IDs
message_ids = [message.id for message in failed_messages]

# Requeue messages from DLQ back to main queue
main_queue = mq.get_queue("orders")
dlq.requeue_messages(message_ids, main_queue)
```

### DLQ Monitoring

It's important to monitor your DLQs regularly:

```python
# Get all queues
queues = mq.list_queues()

# Check DLQs
for queue_info in queues:
    if queue_info.is_dlq and queue_info.message_count > 0:
        print(f"WARNING: DLQ {queue_info.name} has {queue_info.message_count} failed messages")
```

Consider setting up alerts when DLQs grow beyond a certain threshold.

## Message Time-to-Live (TTL)

In many applications, messages become irrelevant after a certain period. LeanMQ supports message TTL to automatically expire old messages:

```python
# Send a message with TTL (30 minutes)
message_data = {"order_id": "12345", "status": "processing"}
ttl_seconds = 30 * 60
main_queue.send_message(message_data, ttl_seconds=ttl_seconds)
```

To process expired messages, you need to periodically call:

```python
# Process expired messages across all queues
expired_count = mq.process_expired_messages()
print(f"Processed {expired_count} expired messages")
```

This would typically be run by a cron job or scheduler.

## Queue Inspection and Monitoring

Understanding the state of your queues is essential for monitoring and debugging:

### Getting Queue Information

```python
# Get information about a specific queue
queue_info = main_queue.get_info()
print(f"Queue: {queue_info.name}")
print(f"Message count: {queue_info.message_count}")
print(f"Consumer group: {queue_info.consumer_group}")
print(f"Pending messages: {queue_info.pending_messages}")
print(f"Created at: {queue_info.created_at}")
```

### Inspecting Queue Contents

Sometimes you need to look at messages without processing them:

```python
# Get messages without consuming them (for inspection)
messages = main_queue.get_messages(count=5, block=False)

for message in messages:
    print(f"Message ID: {message.id}")
    print(f"Data: {message.data}")
    print(f"Timestamp: {message.timestamp}")
    print("---")
    
    # Don't acknowledge these messages since we're just inspecting
```

### Checking Pending Messages

Pending messages are those that have been delivered to a consumer but not yet acknowledged:

```python
# Get info about the queue
queue_info = main_queue.get_info()
print(f"Pending messages: {queue_info.pending_messages}")

# You can also inspect specific pending messages using Redis commands
# (This would require direct Redis client access)
```

A high number of pending messages might indicate a processing bottleneck or failed consumers.

## Queue Purging and Cleanup

Sometimes you need to clear a queue or clean up old messages:

### Purging a Queue

To remove all messages from a queue:

```python
# Remove all messages from the main queue
main_queue.purge()

# Remove all messages from the DLQ
dlq.purge()
```

This is useful for:
- Testing and development
- Recovering from a problem where all messages need to be discarded
- Maintenance operations

### Selective Cleanup

To selectively remove some messages:

```python
# Get messages to inspect
messages = main_queue.get_messages(count=100)

# Identify messages to delete (e.g., older than 7 days)
seven_days_ago = time.time() - (7 * 24 * 60 * 60)
to_delete = [
    message.id for message in messages 
    if message.timestamp < seven_days_ago
]

# Delete the old messages
if to_delete:
    main_queue.delete_messages(to_delete)
    print(f"Deleted {len(to_delete)} old messages")
```

## Advanced Patterns

### Delayed Processing

LeanMQ doesn't have built-in delayed queues, but you can implement this pattern:

```python
# Send a message with a process_after timestamp
message_data = {
    "order_id": "12345",
    "status": "pending",
    "process_after": time.time() + (60 * 60)  # Process after 1 hour
}
main_queue.send_message(message_data)

# When processing messages, check the process_after field
@webhook.get("/delayed/processing/")
def process_with_delay(data):
    process_after = data.get("process_after")
    now = time.time()
    
    # If it's not time to process yet, raise an exception to keep in queue
    if process_after and now < process_after:
        # Calculate seconds remaining
        delay_remaining = int(process_after - now)
        raise Exception(f"Not ready for processing. Retry in {delay_remaining} seconds.")
    
    # Otherwise, process normally
    print(f"Processing message: {data}")
```

### Message Prioritization

You can implement basic prioritization using multiple queues:

```python
# Create priority queues
high_queue, _ = mq.create_queue_pair("orders:high")
medium_queue, _ = mq.create_queue_pair("orders:medium")
low_queue, _ = mq.create_queue_pair("orders:low")

# Send messages to appropriate queue based on priority
def send_order(order_data, priority="medium"):
    if priority == "high":
        high_queue.send_message(order_data)
    elif priority == "medium":
        medium_queue.send_message(order_data)
    else:
        low_queue.send_message(order_data)

# When processing, check high priority queue first, then medium, then low
def process_orders():
    # Try high priority first
    messages = high_queue.get_messages(count=10, block=False)
    if not messages:
        # If no high priority messages, try medium
        messages = medium_queue.get_messages(count=10, block=False)
        if not messages:
            # If no medium priority messages, try low
            messages = low_queue.get_messages(count=10, block=True, timeout=1)
    
    # Process messages
    for message in messages:
        process_order(message.data)
        # Acknowledge the message in the appropriate queue
        if message.id.startswith("high:"):
            high_queue.acknowledge_messages([message.id])
        elif message.id.startswith("medium:"):
            medium_queue.acknowledge_messages([message.id])
        else:
            low_queue.acknowledge_messages([message.id])
```

### Consumer Tags

When multiple consumers process the same queue, it can be helpful to track which consumer is handling which message:

```python
# When getting messages, include a consumer ID/tag
consumer_id = f"worker-{socket.gethostname()}-{os.getpid()}"

messages = queue.get_messages(count=10, consumer_id=consumer_id)

# Now when looking at pending messages, you can see which consumer has them
print(f"Messages being processed by {consumer_id}: {len(messages)}")
```

## Queue Performance Optimization

Here are some tips for optimizing queue performance:

### Batch Processing

Process messages in batches for better throughput:

```python
# Get multiple messages at once
messages = queue.get_messages(count=100)

# Process them in a batch
results = batch_process_messages([m.data for m in messages])

# Acknowledge all at once
queue.acknowledge_messages([m.id for m in messages])
```

### Worker Pool Sizing

For high-volume queues, use multiple workers:

```python
from concurrent.futures import ThreadPoolExecutor

# Create a thread pool for processing messages
with ThreadPoolExecutor(max_workers=10) as executor:
    while True:
        messages = queue.get_messages(count=20)
        if not messages:
            time.sleep(1)
            continue
            
        # Submit each message to the thread pool
        futures = [executor.submit(process_message, msg.data) for msg in messages]
        
        # Wait for all to complete
        for future, message in zip(futures, messages):
            try:
                result = future.result(timeout=30)  # Wait up to 30 seconds
                queue.acknowledge_messages([message.id])  # Acknowledge success
            except Exception as e:
                print(f"Error processing message {message.id}: {e}")
                # Move to DLQ after failure
                queue.move_to_dlq([message.id], f"Processing error: {e}", dlq)
```

### Message Size Considerations

Very large messages can impact performance:

```python
# For large data, consider storing the data elsewhere and just sending a reference
def send_large_message(data):
    if len(json.dumps(data)) > 1024 * 10:  # If larger than 10KB
        # Store the data in a database, object storage, etc.
        storage_id = store_data_externally(data)
        
        # Send only a reference in the message
        queue.send_message({
            "type": "large_data_reference",
            "storage_id": storage_id,
            "created_at": time.time()
        })
    else:
        # Send small data directly
        queue.send_message(data)
```

## Monitoring and Operational Considerations

### Health Checks

Implement queue health checks for monitoring systems:

```python
def check_queue_health():
    health_status = {"status": "healthy", "issues": []}
    
    try:
        # Check Redis connection
        mq.mq._get_redis_client().ping()
        
        # Check all queues
        queues = mq.list_queues()
        
        # Check DLQs
        for queue_info in queues:
            if queue_info.is_dlq and queue_info.message_count > 0:
                health_status["issues"].append({
                    "type": "dlq_not_empty",
                    "queue": queue_info.name,
                    "count": queue_info.message_count
                })
                
        # Check for stalled consumers (pending messages)
        for queue_info in queues:
            if not queue_info.is_dlq and queue_info.pending_messages > 100:
                health_status["issues"].append({
                    "type": "high_pending_messages",
                    "queue": queue_info.name,
                    "count": queue_info.pending_messages
                })
        
        if health_status["issues"]:
            health_status["status"] = "warning"
            
        return health_status
    except Exception as e:
        return {"status": "critical", "error": str(e)}
```

### Backup and Recovery

LeanMQ relies on Redis, so follow Redis backup best practices:

- Configure Redis persistence (AOF, RDB, or both)
- Set up regular Redis backups
- Practice recovery scenarios
- Consider Redis replication for high availability

### Metrics and Monitoring

Track key metrics for your queues:

```python
def collect_queue_metrics():
    metrics = []
    queues = mq.list_queues()
    
    for queue_info in queues:
        metrics.append({
            "metric": "queue.message_count",
            "value": queue_info.message_count,
            "tags": {"queue": queue_info.name, "is_dlq": queue_info.is_dlq}
        })
        
        metrics.append({
            "metric": "queue.pending_messages",
            "value": queue_info.pending_messages,
            "tags": {"queue": queue_info.name, "is_dlq": queue_info.is_dlq}
        })
    
    # Send these metrics to your monitoring system (Prometheus, Datadog, etc.)
    send_metrics(metrics)
```

## Next Steps

Now that you understand advanced queue management with LeanMQ, you can:

- Learn about [transactions](./transactions.md) for atomic operations
- Explore [error handling strategies](./error-handling.md) 
- See how to [scale LeanMQ](./scaling.md) for high-volume applications
- Check out [production deployment best practices](./production.md)

For complete API details, visit the [Queue API reference](/reference/queue.md).
