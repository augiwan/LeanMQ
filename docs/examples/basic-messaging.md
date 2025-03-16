# Basic Messaging Examples

This page provides examples of how to use LeanMQ for basic messaging patterns.

## Producer/Consumer Pattern

This example demonstrates a simple producer/consumer pattern using LeanMQ.

### Producer

```python
import time
import uuid
from leanmq import LeanMQ

def producer_example():
    """Example of a message producer."""
    # Initialize LeanMQ
    mq = LeanMQ(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        prefix="example:",  # Optional prefix for all queue names
    )

    # Create a queue pair (main queue and its DLQ)
    task_queue, task_dlq = mq.create_queue_pair("tasks")
    
    # Send some messages
    for i in range(5):
        # Create a task message
        task_data = {
            "task_id": str(uuid.uuid4()),
            "type": "example_task",
            "params": {
                "number": i,
                "data": f"Sample data {i}"
            },
            "created_at": time.time()
        }
        
        # Send the message to the queue
        message_id = task_queue.send_message(task_data)
        print(f"Sent task {i+1} with ID: {message_id}")
    
    # Close Redis connections
    mq.close()
    
    print("Producer finished")


if __name__ == "__main__":
    producer_example()
```

### Consumer

```python
import time
from leanmq import LeanMQ

def process_task(task_data):
    """Process a task message."""
    # In a real application, this would do meaningful work
    task_id = task_data.get("task_id")
    task_type = task_data.get("type")
    params = task_data.get("params", {})
    
    print(f"Processing task {task_id} of type {task_type}")
    print(f"Parameters: {params}")
    
    # Simulate processing time
    time.sleep(1)
    
    return f"Processed task {task_id}"

def consumer_example():
    """Example of a message consumer."""
    # Initialize LeanMQ
    mq = LeanMQ(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        prefix="example:",  # Same prefix as producer
    )

    # Get the tasks queue
    task_queue = mq.get_queue("tasks")
    if task_queue is None:
        print("Task queue doesn't exist yet")
        return
    
    # Get the DLQ for error handling
    task_dlq = mq.get_dead_letter_queue("tasks")
    
    # Process messages in a loop
    max_iterations = 10  # Limit iterations for this example
    iteration = 0
    
    print("Starting consumer loop...")
    
    while iteration < max_iterations:
        iteration += 1
        
        # Get messages from the queue (with blocking for efficiency)
        messages = task_queue.get_messages(count=3, block_for_seconds=2)
        
        if not messages:
            print("No messages available, waiting...")
            continue
        
        print(f"Retrieved {len(messages)} messages")
        
        # Process each message
        for message in messages:
            try:
                # Process the task
                result = process_task(message.data)
                print(f"Result: {result}")
                
                # Acknowledge successful processing
                task_queue.acknowledge_messages([message.id])
                
            except Exception as e:
                print(f"Error processing message {message.id}: {e}")
                
                # Move failed message to DLQ
                if task_dlq:
                    task_queue.move_to_dlq(
                        [message.id],
                        f"Processing error: {e}",
                        task_dlq
                    )
                    print(f"Moved message {message.id} to DLQ")
    
    # Close Redis connections
    mq.close()
    
    print("Consumer finished")


if __name__ == "__main__":
    consumer_example()
```

## Request/Response Pattern

This example demonstrates a request/response pattern using LeanMQ.

### Server

```python
import time
import uuid
from leanmq import LeanMQ

def run_calculator_server():
    """Run a calculator service that responds to calculation requests."""
    # Initialize LeanMQ
    mq = LeanMQ(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        prefix="calc:",  # Use a prefix to isolate these queues
    )
    
    # Create request queue
    request_queue, request_dlq = mq.create_queue_pair("requests")
    
    print("Calculator server starting...")
    
    try:
        # Process requests in a loop
        while True:
            # Get messages from the request queue
            messages = request_queue.get_messages(count=5, block_for_seconds=2)
            
            for message in messages:
                try:
                    print(f"Processing request: {message.id}")
                    
                    # Extract request data
                    request_data = message.data
                    response_queue_name = request_data.get("response_queue")
                    request_id = request_data.get("request_id")
                    
                    if not response_queue_name or not request_id:
                        raise ValueError("Missing response_queue or request_id")
                    
                    # Get the operation and operands
                    operation = request_data.get("operation")
                    a = request_data.get("a", 0)
                    b = request_data.get("b", 0)
                    
                    # Perform the calculation
                    result = None
                    
                    if operation == "add":
                        result = a + b
                    elif operation == "subtract":
                        result = a - b
                    elif operation == "multiply":
                        result = a * b
                    elif operation == "divide":
                        if b == 0:
                            raise ValueError("Division by zero")
                        result = a / b
                    else:
                        raise ValueError(f"Unknown operation: {operation}")
                    
                    # Create response queue if it doesn't exist
                    response_queue, _ = mq.create_queue_pair(response_queue_name)
                    
                    # Send response
                    response_data = {
                        "request_id": request_id,
                        "result": result,
                        "operation": operation,
                        "a": a,
                        "b": b,
                        "timestamp": time.time()
                    }
                    
                    response_queue.send_message(response_data)
                    print(f"Sent response for request {request_id}: {result}")
                    
                    # Acknowledge the request
                    request_queue.acknowledge_messages([message.id])
                    
                except Exception as e:
                    print(f"Error processing request: {e}")
                    
                    # Try to send error response
                    try:
                        request_id = message.data.get("request_id")
                        response_queue_name = message.data.get("response_queue")
                        
                        if request_id and response_queue_name:
                            response_queue, _ = mq.create_queue_pair(response_queue_name)
                            
                            error_response = {
                                "request_id": request_id,
                                "error": str(e),
                                "timestamp": time.time()
                            }
                            
                            response_queue.send_message(error_response)
                            print(f"Sent error response for request {request_id}")
                    except Exception as response_error:
                        print(f"Failed to send error response: {response_error}")
                    
                    # Move failed request to DLQ
                    request_queue.move_to_dlq(
                        [message.id],
                        f"Processing error: {e}",
                        request_dlq
                    )
    
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        # Close Redis connections
        mq.close()
```

### Client

```python
import time
import uuid
from leanmq import LeanMQ

class CalculatorClient:
    """Client for the calculator service."""
    
    def __init__(self):
        """Initialize the calculator client."""
        # Generate a unique client ID
        self.client_id = str(uuid.uuid4())
        self.response_queue_name = f"responses:{self.client_id}"
        
        # Initialize LeanMQ
        self.mq = LeanMQ(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            prefix="calc:",  # Same prefix as server
        )
        
        # Create request and response queues
        self.request_queue, _ = self.mq.create_queue_pair("requests")
        self.response_queue, _ = self.mq.create_queue_pair(self.response_queue_name)
    
    def calculate(self, operation, a, b, timeout=5):
        """Make a calculation request to the server.
        
        Args:
            operation: Mathematical operation ("add", "subtract", "multiply", "divide")
            a: First operand
            b: Second operand
            timeout: Maximum time to wait for response in seconds
            
        Returns:
            The calculation result
            
        Raises:
            TimeoutError: If no response is received within timeout
            ValueError: If the operation is invalid or fails
        """
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Prepare the request
        request_data = {
            "request_id": request_id,
            "response_queue": self.response_queue_name,
            "operation": operation,
            "a": a,
            "b": b,
            "timestamp": time.time()
        }
        
        # Send the request
        self.request_queue.send_message(request_data)
        print(f"Sent {operation} request: {a} and {b}")
        
        # Wait for the response with timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for responses
            responses = self.response_queue.get_messages(count=10, block_for_seconds=1)
            
            # Look for our response
            for response in responses:
                response_data = response.data
                
                # Check if this is for our request
                if response_data.get("request_id") == request_id:
                    # Acknowledge the response
                    self.response_queue.acknowledge_messages([response.id])
                    
                    # Check for error
                    if "error" in response_data:
                        raise ValueError(f"Calculation error: {response_data['error']}")
                    
                    # Return the result
                    return response_data.get("result")
        
        # Timeout
        raise TimeoutError(f"No response received within {timeout} seconds")
    
    def close(self):
        """Close the client."""
        self.mq.close()


def client_example():
    """Example usage of the calculator client."""
    # Create a client
    client = CalculatorClient()
    
    try:
        # Make some calculation requests
        operations = [
            ("add", 10, 5),
            ("subtract", 20, 7),
            ("multiply", 8, 3),
            ("divide", 100, 4)
        ]
        
        for operation, a, b in operations:
            try:
                result = client.calculate(operation, a, b)
                print(f"{operation}({a}, {b}) = {result}")
            except Exception as e:
                print(f"Error with {operation}: {e}")
        
        # Try a division by zero
        try:
            result = client.calculate("divide", 10, 0)
            print(f"divide(10, 0) = {result}")  # This should fail
        except Exception as e:
            print(f"Expected error: {e}")
        
        # Try an invalid operation
        try:
            result = client.calculate("power", 2, 3)
            print(f"power(2, 3) = {result}")  # This should fail
        except Exception as e:
            print(f"Expected error: {e}")
    
    finally:
        # Close the client
        client.close()
```

## Fan-Out Pattern

This example demonstrates how to implement a fan-out pattern where a single message is delivered to multiple consumers.

```python
import threading
import time
import uuid
from leanmq import LeanMQ

class EventPublisher:
    """Publishes events to a central event queue."""
    
    def __init__(self):
        """Initialize the event publisher."""
        self.mq = LeanMQ(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            prefix="events:",
        )
        
        # Create event queue
        self.event_queue, _ = self.mq.create_queue_pair("main")
    
    def publish_event(self, event_type, event_data):
        """Publish an event to the event queue.
        
        Args:
            event_type: Type of event
            event_data: Event data
            
        Returns:
            Message ID of the published event
        """
        # Create the event message
        event_message = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "data": event_data,
            "timestamp": time.time()
        }
        
        # Publish to the event queue
        message_id = self.event_queue.send_message(event_message)
        print(f"Published event: {event_type}, ID: {message_id}")
        
        return message_id
    
    def close(self):
        """Close the publisher."""
        self.mq.close()


class EventConsumer:
    """Consumes events from the event queue."""
    
    def __init__(self, consumer_id, event_types=None):
        """Initialize the event consumer.
        
        Args:
            consumer_id: Unique identifier for this consumer
            event_types: List of event types to process (None for all)
        """
        self.consumer_id = consumer_id
        self.event_types = event_types
        
        self.mq = LeanMQ(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            prefix="events:",
        )
        
        # Get the event queue
        self.event_queue = self.mq.get_queue("main")
        self.dlq = self.mq.get_dead_letter_queue("main")
        
        # Track running state
        self.running = False
        self.thread = None
    
    def process_event(self, event_data):
        """Process an event.
        
        Args:
            event_data: Event data
            
        Returns:
            True if event was processed successfully, False otherwise
        """
        # Default implementation - subclasses should override
        event_id = event_data.get("event_id")
        event_type = event_data.get("event_type")
        data = event_data.get("data", {})
        
        print(f"[{self.consumer_id}] Processing event: {event_type}, ID: {event_id}")
        print(f"[{self.consumer_id}] Event data: {data}")
        
        # Simulate processing time
        time.sleep(0.5)
        
        return True
    
    def _event_processor(self):
        """Background thread for processing events."""
        print(f"[{self.consumer_id}] Starting event processor")
        
        while self.running:
            try:
                # Get events from the queue
                messages = self.event_queue.get_messages(
                    count=5,
                    block_for_seconds=2,
                    consumer_id=self.consumer_id
                )
                
                for message in messages:
                    try:
                        event_data = message.data
                        event_type = event_data.get("event_type")
                        
                        # Skip events that don't match our filter
                        if self.event_types and event_type not in self.event_types:
                            # Still acknowledge events we're not interested in
                            self.event_queue.acknowledge_messages([message.id])
                            continue
                        
                        # Process the event
                        success = self.process_event(event_data)
                        
                        # Acknowledge successful processing
                        if success:
                            self.event_queue.acknowledge_messages([message.id])
                        else:
                            # Move to DLQ if processing failed
                            self.event_queue.move_to_dlq(
                                [message.id],
                                "Processing returned false",
                                self.dlq
                            )
                    
                    except Exception as e:
                        print(f"[{self.consumer_id}] Error processing event: {e}")
                        
                        # Move to DLQ on error
                        self.event_queue.move_to_dlq(
                            [message.id],
                            f"Processing error: {e}",
                            self.dlq
                        )
            
            except Exception as e:
                print(f"[{self.consumer_id}] Error getting events: {e}")
                time.sleep(1)  # Avoid tight loop on persistent errors
        
        print(f"[{self.consumer_id}] Event processor stopped")
    
    def start(self):
        """Start the event consumer."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._event_processor)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the event consumer."""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
    
    def close(self):
        """Close the consumer and release resources."""
        self.stop()
        self.mq.close()


# Example specialized consumer
class OrderEventConsumer(EventConsumer):
    """Consumer specialized for order events."""
    
    def __init__(self, consumer_id):
        """Initialize the order event consumer."""
        super().__init__(
            consumer_id=consumer_id,
            event_types=["order_created", "order_updated", "order_cancelled"]
        )
    
    def process_event(self, event_data):
        """Process an order event.
        
        Args:
            event_data: Event data
            
        Returns:
            True if event was processed successfully
        """
        event_type = event_data.get("event_type")
        data = event_data.get("data", {})
        
        order_id = data.get("order_id")
        
        print(f"[{self.consumer_id}] Processing order event: {event_type}")
        print(f"[{self.consumer_id}] Order ID: {order_id}")
        
        # Simulate different processing based on event type
        if event_type == "order_created":
            # Simulate order creation logic
            print(f"[{self.consumer_id}] Creating order {order_id}")
            time.sleep(0.7)
        
        elif event_type == "order_updated":
            # Simulate order update logic
            print(f"[{self.consumer_id}] Updating order {order_id}")
            time.sleep(0.5)
        
        elif event_type == "order_cancelled":
            # Simulate order cancellation logic
            print(f"[{self.consumer_id}] Cancelling order {order_id}")
            time.sleep(0.3)
        
        print(f"[{self.consumer_id}] Order event processing completed")
        return True


def fan_out_example():
    """Example of the fan-out pattern."""
    # Create a publisher
    publisher = EventPublisher()
    
    # Create multiple consumers
    consumers = [
        # General consumer that processes all events
        EventConsumer(consumer_id="general-consumer"),
        
        # Specialized consumers
        OrderEventConsumer(consumer_id="order-consumer-1"),
        OrderEventConsumer(consumer_id="order-consumer-2"),
        
        # Consumer only interested in user events
        EventConsumer(
            consumer_id="user-consumer",
            event_types=["user_created", "user_updated"]
        )
    ]
    
    try:
        # Start all consumers
        for consumer in consumers:
            consumer.start()
        
        # Allow consumers to initialize
        time.sleep(1)
        
        # Publish some events
        publisher.publish_event(
            "order_created",
            {
                "order_id": "ORD-12345",
                "user_id": "USR-789",
                "items": [
                    {"product_id": "PROD-A", "quantity": 2, "price": 29.99},
                    {"product_id": "PROD-B", "quantity": 1, "price": 49.99}
                ],
                "total": 109.97
            }
        )
        
        time.sleep(0.5)
        
        publisher.publish_event(
            "user_created",
            {
                "user_id": "USR-790",
                "email": "newuser@example.com",
                "name": "New User"
            }
        )
        
        time.sleep(0.5)
        
        publisher.publish_event(
            "order_updated",
            {
                "order_id": "ORD-12345",
                "status": "processing",
                "updated_by": "system"
            }
        )
        
        # Allow time for processing
        print("\nWaiting for event processing to complete...")
        time.sleep(5)
        
    finally:
        # Clean up
        print("\nShutting down...")
        
        for consumer in consumers:
            consumer.close()
        
        publisher.close()
        
        print("Fan-out example completed")


if __name__ == "__main__":
    fan_out_example()
```

## Next Steps

These examples demonstrate the basic messaging patterns you can implement with LeanMQ. For more advanced usage:

- See the [webhook pattern guide](../guide/webhook-pattern.md) for webhook-like communication between services
- Explore [advanced queue management](../guide/advanced/queue-management.md) for more control over queues
- Check [transactions](../guide/advanced/transactions.md) for atomic operations across multiple queues

For detailed API documentation, visit the [API Reference](../reference/core.md) section.
