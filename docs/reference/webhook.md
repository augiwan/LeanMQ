# Webhook API Reference

This reference documents the webhook-related classes and methods in LeanMQ.

## LeanMQWebhook Class

The `LeanMQWebhook` class provides a webhook-like interface for internal microservice communication using LeanMQ as the underlying message transport mechanism.

### Constructor

```python
LeanMQWebhook(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
    prefix: str = "webhook:",
    process_interval: int = 1,
    auto_start: bool = True
)
```

**Parameters**:
- `redis_host` (str): Redis host
- `redis_port` (int): Redis port
- `redis_db` (int): Redis database
- `redis_password` (Optional[str]): Redis password, if required
- `prefix` (str): Prefix for queue names
- `process_interval` (int): Interval in seconds for processing messages
- `auto_start` (bool): Whether to start processing messages automatically

**Returns**: A new LeanMQWebhook instance

### Methods

#### `get`

```python
get(path: str) -> Callable[[F], F]
```

Decorator for registering a webhook handler.

**Parameters**:
- `path` (str): The path pattern for the webhook

**Returns**: A decorator function to register handlers

**Example**:
```python
@webhook.get("/order/status/")
def process_order_status(data):
    print(f"Order {data['order_id']} status: {data['status']}")
```

#### `send`

```python
send(path: str, data: Dict[str, Any]) -> str
```

Send a webhook event.

**Parameters**:
- `path` (str): The target path for the webhook
- `data` (Dict[str, Any]): The data to send

**Returns**: Message ID

**Example**:
```python
message_id = webhook.send("/order/status/", {
    "order_id": "ORD-12345",
    "status": "shipped"
})
```

#### `process_messages`

```python
process_messages(
    block: bool = False,
    timeout: int = 1,
    count: int = 10
) -> int
```

Process incoming webhook messages.

**Parameters**:
- `block` (bool): Whether to block waiting for messages
- `timeout` (int): How long to block for in seconds
- `count` (int): Maximum number of messages to process per queue

**Returns**: Number of messages processed

**Example**:
```python
processed_count = webhook.process_messages(block=True, timeout=5, count=20)
print(f"Processed {processed_count} messages")
```

#### `run_service`

```python
run_service(
    process_count: int = 10,
    block_for_seconds: Optional[int] = 1,
    handle_signals: bool = True,
    worker_thread_timeout: int = 5,
    log_level: Union[int, str] = logging.INFO
) -> WebhookService
```

Run a webhook service that processes messages in a dedicated worker thread.

**Parameters**:
- `process_count` (int): Maximum number of messages to process in each loop iteration
- `block_for_seconds` (Optional[int]): How long to block waiting for new messages in each iteration
- `handle_signals` (bool): Whether to register signal handlers for graceful shutdown
- `worker_thread_timeout` (int): Timeout in seconds when waiting for worker thread to finish
- `log_level` (Union[int, str]): Logging level for the webhook service

**Returns**: A running WebhookService instance

**Example**:
```python
service = webhook.run_service(
    process_count=20,
    block_for_seconds=2,
    handle_signals=True
)

# Later, stop the service
service.stop()
```

#### `start_processing`

```python
start_processing() -> None
```

Start processing messages in a loop. In a simple implementation, this blocks the current thread.

**Example**:
```python
# This will block until stopped
webhook.start_processing()
```

#### `stop_processing`

```python
stop_processing() -> None
```

Stop processing messages.

**Example**:
```python
webhook.stop_processing()
```

#### `close`

```python
close() -> None
```

Close connections.

**Example**:
```python
webhook.close()
```

### Context Manager Support

The `LeanMQWebhook` class supports the context manager protocol:

```python
with LeanMQWebhook(redis_host="localhost") as webhook:
    # Use webhook here
    @webhook.get("/order/status/")
    def process_order_status(data):
        print(f"Order {data['order_id']} status: {data['status']}")
        
    webhook.send("/order/status/", {"order_id": "ORD-12345", "status": "shipped"})
    webhook.process_messages()
# Redis connections are automatically closed when exiting the context
```

## WebhookService Class

The `WebhookService` class provides a long-running service for processing webhook messages in a dedicated worker thread.

### Constructor

```python
WebhookService(
    webhook: LeanMQWebhook,
    process_count: int = 10,
    block_for_seconds: Optional[int] = 1,
    handle_signals: bool = True,
    worker_thread_timeout: int = 5
)
```

**Parameters**:
- `webhook` (LeanMQWebhook): The LeanMQWebhook instance to use
- `process_count` (int): Maximum number of messages to process in each loop iteration
- `block_for_seconds` (Optional[int]): How long to block waiting for new messages in each iteration
- `handle_signals` (bool): Whether to register signal handlers for graceful shutdown
- `worker_thread_timeout` (int): Timeout in seconds when waiting for worker thread to finish

**Returns**: A new WebhookService instance

### Methods

#### `start`

```python
start() -> None
```

Start the webhook service.

**Example**:
```python
service = WebhookService(webhook=webhook)
service.start()
```

#### `stop`

```python
stop() -> None
```

Stop the webhook service.

**Example**:
```python
service.stop()
```

#### `is_alive`

```python
is_alive() -> bool
```

Check if the service is running and the worker thread is alive.

**Returns**: True if the service is running and the worker thread is alive

**Example**:
```python
if service.is_alive():
    print("Service is running")
else:
    print("Service is not running")
```

## WebhookRoute Class

The `WebhookRoute` class represents a registered webhook route.

### Constructor

```python
WebhookRoute(
    path: str,
    handler: Callable[[Dict[str, Any]], Any],
    queue: Queue
)
```

**Parameters**:
- `path` (str): The path pattern for the webhook
- `handler` (Callable): The function to call when a message arrives
- `queue` (Queue): The LeanMQ queue associated with this route

::: warning
You should not create WebhookRoute objects directly. They are created internally by the LeanMQWebhook.get() decorator.
:::

## Example Usage

### Basic Example

```python
from leanmq import LeanMQWebhook
import time

# Initialize webhook
webhook = LeanMQWebhook(
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    auto_start=False
)

# Register webhook handlers
@webhook.get("/order/status/")
def process_order_status(data):
    print(f"Order {data['order_id']} status: {data['status']}")

@webhook.get("/product/inventory/")
def process_inventory_update(data):
    print(f"Product {data['product_id']} inventory: {data['quantity']}")

# Send webhook events
webhook.send("/order/status/", {"order_id": "ORD-12345", "status": "shipped"})
webhook.send("/product/inventory/", {"product_id": "PROD-789", "quantity": 150})

# Process incoming webhooks
webhook.process_messages(block=True, timeout=1)

# Close connections when done
webhook.close()
```

### Running as a Service

```python
from leanmq import LeanMQWebhook
import time

# Initialize webhook
webhook = LeanMQWebhook(redis_host="localhost", redis_port=6379)

# Register webhook handlers
@webhook.get("/order/status/")
def process_order_status(data):
    print(f"Order {data['order_id']} status: {data['status']}")

# Start the webhook service (background thread)
service = webhook.run_service()

# Send some webhook events
webhook.send("/order/status/", {"order_id": "ORD-12345", "status": "processing"})
webhook.send("/order/status/", {"order_id": "ORD-12345", "status": "shipped"})

try:
    # Keep the main thread running
    while service.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
finally:
    # Stop the service
    service.stop()
    webhook.close()
```

## Related

- [Core API](./core.md): Documentation for the LeanMQ class and related methods
- [Queue API](./queue.md): Documentation for the Queue class used by webhooks
