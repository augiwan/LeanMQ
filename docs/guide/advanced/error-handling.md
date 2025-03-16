# Error Handling & Resilience

This guide covers advanced error handling techniques in LeanMQ to build resilient, fault-tolerant applications that can gracefully handle failures.

## Understanding Error Scenarios

When building distributed systems with message queues, various errors can occur:

1. **Message processing errors**: Exceptions during message processing
2. **Connection failures**: Redis server unavailability
3. **Expired messages**: Messages with TTL that weren't processed in time
4. **Poison messages**: Malformed messages that consistently cause errors
5. **System failures**: Application crashes or container restarts

LeanMQ provides mechanisms to handle all these scenarios properly.

## Exception Handling in Message Processors

When processing messages, it's crucial to have proper exception handling:

```python
@webhook.get("/order/status/")
def process_order_status(data):
    try:
        # Validate input
        if "order_id" not in data or "status" not in data:
            raise ValueError("Missing required fields")
            
        # Process the message
        order_id = data["order_id"]
        status = data["status"]
        process_order(order_id, status)
        
    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error: {e}")
        # Re-raise to move to DLQ - this is a permanent error
        raise
        
    except TemporaryError as e:
        # Handle temporary errors (like service unavailability)
        logger.warning(f"Temporary error: {e}")
        # Re-raise to keep in queue for retry
        raise
        
    except Exception as e:
        # Handle unexpected errors
        logger.exception(f"Unexpected error processing order {data.get('order_id')}: {e}")
        # Re-raise to move to DLQ
        raise
```

### Error Classification

It's helpful to classify errors into different categories:

1. **Permanent errors**: No matter how many times you retry, these will never succeed (e.g., validation errors)
2. **Temporary errors**: These might succeed if retried (e.g., network timeouts, database deadlocks)
3. **Application bugs**: These are programming errors that need to be fixed

Your error handling strategy should depend on the error type.

## Using Dead Letter Queues

Dead letter queues (DLQs) are critical for handling failed messages:

```python
# Get the DLQ for a queue
dlq = mq.get_dead_letter_queue("orders")

# Get failed messages from the DLQ
failed_messages = dlq.get_messages(count=10)

for message in failed_messages:
    # Log details about the failed message
    logger.error(f"Failed message ID: {message.id}")
    logger.error(f"Message data: {message.data}")
    logger.error(f"Delivery attempts: {message.delivery_count}")
    
    try:
        # Try to fix and manually process
        fixed_data = fix_message_data(message.data)
        process_order_manually(fixed_data)
        
        # Acknowledge the message in the DLQ
        dlq.acknowledge_messages([message.id])
    except Exception as e:
        logger.error(f"Manual processing also failed: {e}")
```

### Automatic DLQ Monitoring

Set up periodic checking of DLQs:

```python
def monitor_dlqs():
    """Monitor dead letter queues and send alerts for failed messages."""
    while True:
        try:
            queues = mq.list_queues()
            
            for queue_info in queues:
                if queue_info.is_dlq and queue_info.message_count > 0:
                    # Alert on non-empty DLQs
                    logger.warning(f"DLQ {queue_info.name} has {queue_info.message_count} failed messages")
                    
                    # Optionally send alerts via email, Slack, etc.
                    send_alert(f"DLQ {queue_info.name} has {queue_info.message_count} failed messages")
        except Exception as e:
            logger.error(f"Error monitoring DLQs: {e}")
            
        # Check every few minutes
        time.sleep(300)
```

## Implementing Retry Logic

For transient errors, implement retry logic with exponential backoff:

```python
import random
import time
from functools import wraps

def with_retry(max_attempts=3, initial_backoff=1, max_backoff=60):
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            backoff = initial_backoff
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except TemporaryError as e:  # Only retry on temporary errors
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Final attempt failed: {e}")
                        raise
                        
                    # Calculate backoff with jitter to avoid thundering herd
                    jitter = random.uniform(0.8, 1.2)
                    sleep_time = min(backoff * jitter, max_backoff)
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {sleep_time:.2f} seconds..."
                    )
                    
                    time.sleep(sleep_time)
                    backoff = min(backoff * 2, max_backoff)  # Exponential growth
                    
        return wrapper
    return decorator

# Usage example
@with_retry(max_attempts=5, initial_backoff=2)
def process_payment(order_id, amount):
    response = payment_gateway.charge(order_id, amount)
    if response.status_code == 503:  # Service Unavailable
        raise TemporaryError("Payment gateway unavailable")
    elif response.status_code != 200:
        raise ValueError(f"Payment failed: {response.text}")
    return response.json()
```

### Retrying from Dead Letter Queues

Periodically retry messages in DLQs that might have failed due to temporary issues:

```python
def retry_dlq_messages():
    """Retry messages from DLQs that might have failed due to temporary issues."""
    queues = mq.list_queues()
    requeued_count = 0
    
    for queue_info in queues:
        if queue_info.is_dlq and queue_info.message_count > 0:
            # Get the original queue name (remove the :dlq suffix)
            original_queue_name = queue_info.name.rsplit(":dlq", 1)[0]
            
            # Get the queues
            dlq = mq.get_queue(queue_info.name)
            original_queue = mq.get_queue(original_queue_name)
            
            if dlq and original_queue:
                # Get messages from the DLQ
                failed_messages = dlq.get_messages(count=100)
                
                # Retry messages that might succeed now
                for message in failed_messages:
                    # Check if this looks like a temporary error
                    if is_temporary_error(message.data.get("_error", "")):
                        # Requeue the message
                        dlq.requeue_messages([message.id], original_queue)
                        requeued_count += 1
    
    logger.info(f"Requeued {requeued_count} messages from DLQs")
    return requeued_count

def is_temporary_error(error_message):
    """Check if an error message indicates a temporary error."""
    temporary_patterns = [
        "connection refused",
        "timeout",
        "temporarily unavailable",
        "too many connections",
        "rate limit exceeded",
        "503",  # Service Unavailable
        "retry"
    ]
    
    error_message = error_message.lower()
    return any(pattern in error_message for pattern in temporary_patterns)
```

## Handling Connection Failures

LeanMQ includes built-in connection retry logic, but you can enhance it:

```python
try:
    # Try to connect and perform operations
    webhook = LeanMQWebhook(
        redis_host="redis.example.com",
        redis_port=6379,
        redis_db=0
    )
    
    # Register handlers and start service
    # ...
    
except ConnectionError as e:
    logger.critical(f"Could not connect to Redis: {e}")
    # Send alerts and initiate fallback procedures
    send_critical_alert("Redis connection failed", str(e))
    start_fallback_processing()
```

### Connection Health Check

Implement a health check to regularly verify Redis connectivity:

```python
def check_redis_connection():
    """Check the Redis connection health."""
    try:
        # Try a simple ping operation
        mq.mq._get_redis_client().ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection check failed: {e}")
        return False

def health_check():
    """Perform a complete system health check."""
    health_status = {"status": "healthy", "components": {}}
    
    # Check Redis connection
    redis_healthy = check_redis_connection()
    health_status["components"]["redis"] = {
        "status": "healthy" if redis_healthy else "unhealthy",
        "details": "Connection OK" if redis_healthy else "Connection failed"
    }
    
    # Check DLQs
    dlq_status = "healthy"
    dlq_details = "No failed messages"
    
    try:
        queues = mq.list_queues()
        dlq_count = 0
        
        for queue_info in queues:
            if queue_info.is_dlq and queue_info.message_count > 0:
                dlq_count += 1
                
        if dlq_count > 0:
            dlq_status = "warning"
            dlq_details = f"{dlq_count} DLQs have messages"
    except Exception as e:
        dlq_status = "unknown"
        dlq_details = f"Could not check DLQs: {e}"
        
    health_status["components"]["dlq"] = {
        "status": dlq_status,
        "details": dlq_details
    }
    
    # Set overall status (worst of all components)
    if any(comp["status"] == "unhealthy" for comp in health_status["components"].values()):
        health_status["status"] = "unhealthy"
    elif any(comp["status"] == "warning" for comp in health_status["components"].values()):
        health_status["status"] = "warning"
        
    return health_status
```

## Handling Poison Messages

Poison messages can cause repeated failures. Handle them specially:

```python
@webhook.get("/data/process/")
def process_data(data):
    try:
        # Process the data
        result = complex_processing(data)
        return result
    except Exception as e:
        # Check if this might be a poison message
        is_poison = is_likely_poison_message(data, str(e))
        
        if is_poison:
            logger.error(f"Detected poison message: {data}, Error: {e}")
            
            # Store the message for later analysis
            store_poison_message(data, str(e))
            
            # Don't re-raise, just acknowledge to remove from queue
            return
        else:
            # Regular error, re-raise to move to DLQ
            raise

def is_likely_poison_message(data, error_message):
    """Check if a message is likely a poison message that will never process correctly."""
    # Check for structural issues that indicate the message is fundamentally broken
    if not isinstance(data, dict):
        return True
        
    # Check for known patterns that cause unrecoverable errors
    if "divide by zero" in error_message:
        return True
        
    # Check if data is missing critical fields
    required_fields = ["id", "type", "payload"]
    if not all(field in data for field in required_fields):
        return True
        
    return False

def store_poison_message(data, error):
    """Store a poison message for later analysis."""
    # In a real implementation, this might store to a database
    with open("poison_messages.jsonl", "a") as f:
        record = {
            "timestamp": time.time(),
            "data": data,
            "error": error
        }
        f.write(json.dumps(record) + "\n")
```

## Resilient Service Design

To make your webhook service more resilient:

### 1. Graceful Shutdown

Ensure proper handling of shutdown signals:

```python
def main():
    # Initialize the service
    service = webhook.run_service(handle_signals=True)
    
    try:
        # Main application loop
        while service.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        # Always ensure clean shutdown
        logger.info("Performing graceful shutdown...")
        service.stop()
        webhook.close()
```

### 2. Circuit Breaker Pattern

Implement circuit breakers for external dependencies:

```python
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures with external dependencies."""
    
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, don't attempt
    HALF_OPEN = "half-open"  # Testing if recovered
    
    def __init__(self, failure_threshold=5, reset_timeout=60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = self.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        self.lock = threading.RLock()
        
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                if self.state == self.OPEN:
                    # Check if it's time to try again
                    if time.time() - self.last_failure_time > self.reset_timeout:
                        logger.info("Circuit breaker state: HALF-OPEN")
                        self.state = self.HALF_OPEN
                    else:
                        raise CircuitBreakerError("Circuit breaker is OPEN")
                        
            try:
                result = func(*args, **kwargs)
                
                # Success, reset if in half-open state
                with self.lock:
                    if self.state == self.HALF_OPEN:
                        logger.info("Circuit breaker state: CLOSED")
                        self.state = self.CLOSED
                        self.failures = 0
                        
                return result
                
            except Exception as e:
                with self.lock:
                    self.failures += 1
                    self.last_failure_time = time.time()
                    
                    if self.state == self.CLOSED and self.failures >= self.failure_threshold:
                        logger.warning("Circuit breaker state: OPEN")
                        self.state = self.OPEN
                    elif self.state == self.HALF_OPEN:
                        logger.warning("Circuit breaker state: OPEN (half-open failed)")
                        self.state = self.OPEN
                        
                raise
                
        return wrapper

class CircuitBreakerError(Exception):
    """Raised when a service call is prevented by the circuit breaker."""
    pass

# Usage example
payment_circuit = CircuitBreaker(failure_threshold=3, reset_timeout=30)

@payment_circuit
def process_payment(order_id, amount):
    # Call external payment service
    return payment_gateway.charge(order_id, amount)

# In webhook handler
@webhook.get("/order/payment/")
def handle_payment(data):
    try:
        process_payment(data["order_id"], data["amount"])
    except CircuitBreakerError:
        # Payment service is having issues
        logger.error("Payment service unavailable, queuing for later retry")
        store_for_later_processing(data)
        
        # Acknowledge the message but don't consider it successfully processed
        return "payment_service_unavailable"
```

### 3. Monitoring and Alerting

Set up proper monitoring:

```python
def monitor_webhook_service():
    """Monitor the webhook service and collect metrics."""
    while True:
        try:
            # Collect metrics
            metrics = {}
            
            # Check queues
            queues = mq.list_queues()
            for queue_info in queues:
                queue_type = "dlq" if queue_info.is_dlq else "queue"
                metrics[f"{queue_info.name}.message_count"] = queue_info.message_count
                metrics[f"{queue_info.name}.pending_messages"] = queue_info.pending_messages
            
            # Check Redis health
            redis_healthy = check_redis_connection()
            metrics["redis.healthy"] = 1 if redis_healthy else 0
            
            # Check service health
            service_healthy = service.is_alive()
            metrics["service.healthy"] = 1 if service_healthy else 0
            
            # Send metrics to monitoring system
            send_metrics(metrics)
            
            # Check for alert conditions
            for queue_info in queues:
                if queue_info.is_dlq and queue_info.message_count > 10:
                    send_alert(f"DLQ {queue_info.name} has {queue_info.message_count} failed messages")
                elif not queue_info.is_dlq and queue_info.pending_messages > 100:
                    send_alert(f"Queue {queue_info.name} has {queue_info.pending_messages} pending messages")
                    
            if not redis_healthy:
                send_alert("Redis connection is unhealthy")
                
            if not service_healthy:
                send_alert("Webhook service is not running")
                
        except Exception as e:
            logger.error(f"Error in monitoring: {e}")
            
        # Check every minute
        time.sleep(60)
```

## Error Logging Best Practices

Implement comprehensive error logging:

```python
import logging
import traceback
import uuid

def setup_logging():
    """Set up proper logging for error tracking."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] %(message)s",
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    
    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    for handler in logging.root.handlers:
        handler.addFilter(correlation_filter)
        
class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation IDs to log records."""
    
    def __init__(self):
        super().__init__()
        self._local = threading.local()
        
    def get_correlation_id(self):
        if not getattr(self._local, "correlation_id", None):
            self._local.correlation_id = str(uuid.uuid4())
        return self._local.correlation_id
        
    def set_correlation_id(self, correlation_id):
        self._local.correlation_id = correlation_id
        
    def filter(self, record):
        record.correlation_id = getattr(self._local, "correlation_id", "-")
        return True

correlation_filter = CorrelationIdFilter()
logger = logging.getLogger(__name__)

def log_webhook_error(webhook_path, message_data, error):
    """Log detailed error information for webhook processing failures."""
    try:
        # Set correlation ID based on message ID or create a new one
        correlation_id = message_data.get("_correlation_id", str(uuid.uuid4()))
        correlation_filter.set_correlation_id(correlation_id)
        
        # Basic error info
        logger.error(f"Error processing webhook {webhook_path}: {error}")
        
        # Detailed error context
        error_context = {
            "webhook_path": webhook_path,
            "message_data": message_data,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc()
        }
        
        logger.error(f"Error details: {json.dumps(error_context, default=str)}")
    except Exception as e:
        # Fallback if detailed logging fails
        logger.error(f"Error in logging (meta-error): {e}")
        logger.error(f"Original error: {error}")
```

## Handling System Failures

For unexpected system failures (crashes, reboots):

```python
def start_webhook_service_with_recovery():
    """Start the webhook service with recovery from unexpected failures."""
    # Check for pending messages from previous runs
    try:
        queues = mq.list_queues()
        pending_count = 0
        
        for queue_info in queues:
            if not queue_info.is_dlq and queue_info.pending_messages > 0:
                pending_count += queue_info.pending_messages
                
        if pending_count > 0:
            logger.warning(f"Found {pending_count} pending messages from previous run")
            
            # Consider automatically acknowledging or requeuing very old pending messages
            # that may be stuck from a previous crash
            recover_stuck_messages()
            
    except Exception as e:
        logger.error(f"Error during recovery check: {e}")
        
    # Start the service normally
    service = webhook.run_service()
    return service

def recover_stuck_messages():
    """Recover messages that might be stuck from a previous crash."""
    # This requires direct Redis access to examine pending entries
    redis_client = mq.mq._get_redis_client()
    
    queues = mq.list_queues()
    for queue_info in queues:
        if not queue_info.is_dlq and queue_info.pending_messages > 0:
            # Get pending entries older than 1 hour (indicating they're stuck)
            one_hour_ago_ms = (time.time() - 3600) * 1000
            
            # This is a Redis Streams command to get pending messages
            # You might need to adapt this based on your Redis client
            pending = redis_client.xpending(
                queue_info.name,
                queue_info.consumer_group,
                min="-",
                max="+",
                count=100
            )
            
            for entry in pending:
                # entry format: [message_id, consumer, idle_time_ms, delivery_count]
                message_id, consumer, idle_time_ms, delivery_count = entry
                
                if idle_time_ms > 3600000:  # Older than 1 hour
                    logger.warning(
                        f"Found stuck message {message_id} in {queue_info.name}, "
                        f"idle for {idle_time_ms/1000:.1f} seconds, "
                        f"delivery count: {delivery_count}"
                    )
                    
                    # Option 1: Acknowledge the message (if we think it was processed)
                    # queue = mq.get_queue(queue_info.name)
                    # queue.acknowledge_messages([message_id])
                    
                    # Option 2: Reclaim and move to DLQ (if we think it failed)
                    # TODO: Implement claim and move to DLQ
                    
                    # Option 3: Reclaim and requeue (retry processing)
                    # TODO: Implement claim and requeue
```

## Next Steps

Now that you understand error handling in LeanMQ, you can:

- Learn about [scaling LeanMQ](./scaling.md) for high-volume applications
- Explore [production deployment best practices](./production.md)
- Check the [exception reference](../../reference/exceptions.md) for details on specific exceptions

Remember that robust error handling is essential for building reliable message processing systems. Take the time to implement proper error classification, retry logic, monitoring, and DLQ management in your applications.
