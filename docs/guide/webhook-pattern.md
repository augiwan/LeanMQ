# The Webhook Pattern in LeanMQ

One of LeanMQ's most powerful features is its webhook-like interface, which provides a familiar and intuitive API for service-to-service communication. This guide explores how to use this pattern effectively in your applications.

## What is the Webhook Pattern?

The webhook pattern is a communication mechanism where one service sends an HTTP request to another service when a specific event occurs. It's a popular way to implement event-driven architectures and integrate different systems.

Traditional webhooks have several challenges:
- They rely on HTTP, which can fail due to network issues
- If the receiving service is down, the webhook is typically lost
- Implementing retry logic is complex and often error-prone
- Scaling webhook handling requires careful design

LeanMQ provides a webhook-like interface that addresses these challenges by using Redis Streams as the underlying transport mechanism, offering persistence, reliability, and scalability.

## Setting Up LeanMQWebhook

First, initialize the LeanMQWebhook class:

```python
from leanmq import LeanMQWebhook

webhook = LeanMQWebhook(
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    prefix="webhook:",       # Optional prefix for queue names
    process_interval=1,      # Interval in seconds for processing messages
    auto_start=False         # Whether to start processing messages automatically
)
```

## Registering Webhook Handlers

The LeanMQWebhook API uses a decorator pattern similar to web frameworks like Flask or FastAPI:

```python
@webhook.get("/order/status/")
def process_order_status(data):
    """Process order status updates."""
    order_id = data.get("order_id")
    status = data.get("status")
    print(f"Order {order_id} status updated to: {status}")
    
    # Your business logic here...
    if status == "shipped":
        send_shipping_notification(order_id)

@webhook.get("/product/inventory/")
def process_inventory_update(data):
    """Process inventory updates."""
    product_id = data.get("product_id")
    quantity = data.get("quantity")
    print(f"Product {product_id} inventory updated to: {quantity}")
    
    # Your business logic here...
    if quantity < 10:
        trigger_restock_alert(product_id)
```

Behind the scenes, LeanMQWebhook:
1. Creates a queue for each path pattern
2. Maps the path to a specific queue name
3. Registers your handler function to be called when messages arrive on that queue

## Sending Webhook Events

To send a webhook event, simply call the `send()` method with the path and data:

```python
# Send an order status update
webhook.send(
    "/order/status/",
    {
        "order_id": "ORD-12345",
        "status": "shipped",
        "updated_at": time.time()
    }
)

# Send an inventory update
webhook.send(
    "/product/inventory/",
    {
        "product_id": "PROD-789",
        "name": "Wireless Headphones",
        "quantity": 5,
        "updated_at": time.time()
    }
)
```

The path is used to determine which queue to send the message to, and which handler will process it.

## Processing Webhook Messages

There are multiple ways to process webhook messages, depending on your application's needs:

### 1. Manual Processing

For simple use cases or testing, you can manually process messages:

```python
# Process messages (optionally blocking until a message is received)
processed_count = webhook.process_messages(
    block=True,       # Whether to block waiting for messages
    timeout=5,        # How long to block (in seconds)
    count=10          # Maximum number of messages to process per queue
)
print(f"Processed {processed_count} webhook(s)")
```

This approach is useful for:
- CRON-based processing
- Single-run scripts
- Testing and debugging

### 2. Running a Webhook Service

For continuous processing in production, use the `run_service()` method:

```python
# Start a webhook service that processes messages in a background thread
service = webhook.run_service(
    process_count=10,            # Maximum messages to process per iteration
    block_for_seconds=1,         # How long to block waiting for new messages
    handle_signals=True,         # Register signal handlers for graceful shutdown
    worker_thread_timeout=5,     # Timeout when waiting for worker thread to finish
    log_level=logging.INFO       # Logging level for the webhook service
)

try:
    # Your main application code here...
    while service.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
finally:
    # Stop the service when done
    service.stop()
    webhook.close()
```

This approach:
- Creates a background thread for processing messages
- Handles proper shutdown on SIGINT and SIGTERM signals
- Provides logging and error handling
- Makes it easy to integrate with your existing application

### 3. Advanced: Custom WebhookService

For even more control, you can create a custom WebhookService directly:

```python
from leanmq import LeanMQWebhook, WebhookService

# Initialize webhook
webhook = LeanMQWebhook(redis_host="localhost", redis_port=6379, redis_db=0)

# Register handlers
@webhook.get("/some/path/")
def handler(data):
    # ...

# Create a custom service with specific settings
service = WebhookService(
    webhook=webhook,
    process_count=20,
    block_for_seconds=2,
    handle_signals=True,
    worker_thread_timeout=10
)

# Start the service
service.start()

# Later, stop the service
service.stop()
```

This approach gives you full control over the service's behavior and lifecycle.

## Path Patterns and Routing

LeanMQWebhook uses a simple path-based routing system:

- Paths should start with a `/`
- Use `/` to separate path segments
- Paths are converted to queue names internally

For example:
- `/order/status/` → `order_status` queue
- `/product/inventory/` → `product_inventory` queue

LeanMQ doesn't currently support wildcards or path parameters like `/orders/{id}/status`, but you can implement your own routing logic inside the handler functions.

## Error Handling and Retries

LeanMQWebhook automatically handles errors during message processing:

1. If a handler function raises an exception, the message is moved to a dead letter queue
2. The exception is logged for debugging
3. Processing continues with the next message

To manually handle retries, you can:

```python
@webhook.get("/order/processing/")
def process_order(data):
    try:
        # Your processing logic here...
        process_order_in_external_system(data)
    except TemporaryError as e:
        # For temporary errors, you might want to "fail" the processing
        # so the message stays in the queue and will be retried automatically
        logger.warning(f"Temporary error processing order {data['order_id']}: {e}")
        raise
    except PermanentError as e:
        # For permanent errors, you might want to handle the failure
        # but acknowledge the message so it's not retried
        logger.error(f"Permanent error processing order {data['order_id']}: {e}")
        record_failed_order(data['order_id'], str(e))
        # Don't re-raise the exception if you want to acknowledge the message
```

## Monitoring and Debugging

To monitor your webhook processing:

1. Check queue information:
   ```python
   queue_info = webhook.mq.get_queue("order_status").get_info()
   print(f"Queue: {queue_info.name}")
   print(f"Message count: {queue_info.message_count}")
   print(f"Pending messages: {queue_info.pending_messages}")
   ```

2. Inspect the dead letter queue:
   ```python
   dlq = webhook.mq.get_dead_letter_queue("order_status")
   failed_messages = dlq.get_messages(count=10)
   
   for message in failed_messages:
       print(f"Failed message ID: {message.id}")
       print(f"Data: {message.data}")
       print(f"Delivery count: {message.delivery_count}")
   ```

3. Reprocess failed messages:
   ```python
   # Move messages from DLQ back to the main queue
   dlq.requeue_messages([message.id for message in failed_messages])
   ```

## Best Practices

Here are some tips for using LeanMQWebhook effectively:

1. **Use meaningful path patterns:**
   - Group related functionality (e.g., `/order/status/`, `/order/payment/`)
   - Use consistent naming conventions

2. **Keep handlers focused:**
   - A handler should do one thing well
   - Split complex processing into multiple handlers if necessary

3. **Use error handling:**
   - Catch and handle expected exceptions
   - Let unexpected exceptions propagate to the DLQ

4. **Monitor your DLQs:**
   - Set up alerts for messages in DLQs
   - Regularly inspect and handle failed messages

5. **Close connections properly:**
   - Use the `with` statement or explicitly call `close()` when done
   - Stop services gracefully before shutdown

6. **Consider message volume:**
   - Adjust `process_count` based on message volume and processing speed
   - For high-volume applications, consider multiple webhook service instances

## Next Steps

Now that you understand the webhook pattern in LeanMQ, you can:

- Learn about [advanced queue management](./advanced/queue-management.md)
- Explore [error handling strategies](./advanced/error-handling.md)
- See how to [scale LeanMQ](./advanced/scaling.md) for high-volume applications
- Check out the [WebhookService API reference](../reference/webhook.md) for complete details

For real-world example applications, visit the [Examples](../examples/webhook-services.md) section.
