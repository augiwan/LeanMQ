# Event-Driven Architecture (Continued)

## Running the Event-Driven System

The following code demonstrates how to run our event-driven microservice system:

```python
def event_driven_architecture_example():
    """Example of an event-driven architecture using LeanMQ."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create services
    order_service = OrderService()
    payment_service = PaymentService()
    shipping_service = ShippingService()
    notification_service = NotificationService()
    
    try:
        # Start all services
        for service in [order_service, payment_service, shipping_service, notification_service]:
            service.start()
        
        # Allow services to initialize
        time.sleep(2)
        
        # Create some orders
        order_ids = []
        
        for i in range(3):
            user_id = f"user-{uuid.uuid4().hex[:8]}"
            items = [
                {
                    "product_id": f"prod-{uuid.uuid4().hex[:8]}",
                    "name": f"Product {i+1}",
                    "price": 19.99 + i * 10,
                    "quantity": i + 1
                },
                {
                    "product_id": f"prod-{uuid.uuid4().hex[:8]}",
                    "name": f"Accessory {i+1}",
                    "price": 5.99,
                    "quantity": 1
                }
            ]
            
            order_id = order_service.create_order(user_id, items)
            order_ids.append(order_id)
            
            # Wait a bit between orders
            time.sleep(1)
        
        # Wait for all events to be processed
        print("\nWaiting for all events to be processed...")
        time.sleep(10)
        
        # Show final order states
        print("\nFinal order states:")
        for order_id in order_ids:
            if order_id in order_service.orders:
                order = order_service.orders[order_id]
                print(f"Order {order_id}: {order['status']}")
                if "tracking_number" in order:
                    print(f"  Tracking: {order['tracking_number']} ({order['carrier']})")
                if "payment_id" in order:
                    print(f"  Payment: {order['payment_id']}")
                print()
    
    finally:
        # Shut down all services
        print("\nShutting down services...")
        for service in [order_service, payment_service, shipping_service, notification_service]:
            service.close()
        
        print("Event-driven architecture example completed")


if __name__ == "__main__":
    event_driven_architecture_example()
```

## API Gateway Pattern

This is another common microservice communication pattern. In this pattern, an API Gateway serves as a single entry point for clients and routes requests to appropriate internal services.

Here's how you could implement a simple API Gateway using LeanMQ's webhook pattern:

```python
import json
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from leanmq import LeanMQWebhook


class ApiGateway:
    """API Gateway that routes requests to internal services."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        self.webhook = LeanMQWebhook(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            prefix="api-gateway:",
            auto_start=False
        )
        
        # Start the webhook service
        self.service = self.webhook.run_service()
        
        # Map of request IDs to responses (for request-response pattern)
        self.pending_responses = {}
        self.response_lock = threading.Lock()
        
        # Register internal route handlers
        self._register_routes()
        
        print("API Gateway started")
    
    def _register_routes(self):
        """Register internal route handlers for service responses."""
        
        @self.webhook.get("/responses/")
        def handle_response(data):
            """Handle responses from internal services."""
            request_id = data.get("request_id")
            if request_id:
                with self.response_lock:
                    self.pending_responses[request_id] = data
    
    def route_request(self, service: str, endpoint: str, data: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        """Route a request to an internal service and wait for response.
        
        Args:
            service: Service name
            endpoint: Service endpoint
            data: Request data
            timeout: Timeout in seconds
            
        Returns:
            Response data
            
        Raises:
            TimeoutError: If no response received within timeout
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Add request metadata
        request_data = data.copy()
        request_data["request_id"] = request_id
        request_data["timestamp"] = time.time()
        request_data["response_path"] = "/responses/"
        
        # Send request to service
        path = f"/{service}/{endpoint}/"
        self.webhook.send(path, request_data)
        
        print(f"Routed request to {path}, ID: {request_id}")
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.response_lock:
                if request_id in self.pending_responses:
                    response = self.pending_responses.pop(request_id)
                    return response
            
            # Brief delay to avoid tight loop
            time.sleep(0.1)
        
        # Timeout reached
        raise TimeoutError(f"No response received from {service}/{endpoint} within {timeout} seconds")
    
    def close(self):
        """Close the API Gateway."""
        if self.service:
            self.service.stop()
        self.webhook.close()
        print("API Gateway stopped")


class OrderServiceClient:
    """Client for the Order Service."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        self.webhook = LeanMQWebhook(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            prefix="api-gateway:",
            auto_start=False
        )
        
        # Start the webhook service
        self.service = self.webhook.run_service()
        
        # Register route handlers
        self._register_routes()
        
        print("Order Service started")
    
    def _register_routes(self):
        """Register route handlers."""
        
        @self.webhook.get("/orders/create/")
        def handle_create_order(data):
            """Handle order creation requests."""
            request_id = data.get("request_id")
            response_path = data.get("response_path")
            
            # Process order creation
            print(f"Processing order creation: {data}")
            
            # Simulate processing time
            time.sleep(1.5)
            
            # Generate order ID
            order_id = f"order-{uuid.uuid4().hex[:8]}"
            
            # Send response
            response = {
                "request_id": request_id,
                "order_id": order_id,
                "status": "created",
                "message": "Order created successfully",
                "timestamp": time.time()
            }
            
            self.webhook.send(response_path, response)
            print(f"Sent response for request {request_id}")
        
        @self.webhook.get("/orders/status/")
        def handle_order_status(data):
            """Handle order status requests."""
            request_id = data.get("request_id")
            response_path = data.get("response_path")
            order_id = data.get("order_id")
            
            # Process order status request
            print(f"Processing order status request for {order_id}")
            
            # Simulate processing time
            time.sleep(0.8)
            
            # Simulate random order status
            statuses = ["processing", "shipped", "delivered", "cancelled"]
            status = statuses[uuid.uuid4().int % len(statuses)]
            
            # Send response
            response = {
                "request_id": request_id,
                "order_id": order_id,
                "status": status,
                "updated_at": time.time(),
                "timestamp": time.time()
            }
            
            self.webhook.send(response_path, response)
            print(f"Sent response for request {request_id}")
    
    def close(self):
        """Close the service."""
        if self.service:
            self.service.stop()
        self.webhook.close()
        print("Order Service stopped")


def api_gateway_example():
    """Example of API Gateway pattern using LeanMQ."""
    # Create API Gateway and services
    gateway = ApiGateway()
    order_service = OrderServiceClient()
    
    try:
        # Allow services to initialize
        time.sleep(2)
        
        # Create an order through the gateway
        try:
            response = gateway.route_request(
                service="orders",
                endpoint="create",
                data={
                    "user_id": "user-12345",
                    "items": [
                        {"product_id": "prod-789", "quantity": 2, "price": 29.99},
                        {"product_id": "prod-456", "quantity": 1, "price": 49.99}
                    ],
                    "shipping_address": "123 Main St, Anytown, US 12345"
                }
            )
            
            print(f"\nOrder creation response: {json.dumps(response, indent=2)}")
            
            # Get the order status
            order_id = response.get("order_id")
            
            status_response = gateway.route_request(
                service="orders",
                endpoint="status",
                data={"order_id": order_id}
            )
            
            print(f"\nOrder status response: {json.dumps(status_response, indent=2)}")
            
        except TimeoutError as e:
            print(f"Error: {e}")
    
    finally:
        # Clean up
        gateway.close()
        order_service.close()
        
        print("API Gateway example completed")


if __name__ == "__main__":
    api_gateway_example()
```

## Summary

These examples demonstrate how to implement common microservice communication patterns using LeanMQ:

1. **Event-Driven Architecture**: Services communicate by publishing and subscribing to events. This provides loose coupling and allows for reactive processing.

2. **API Gateway Pattern**: A central gateway routes client requests to appropriate internal services, providing a single entry point and abstracting the internal architecture.

Both patterns leverage LeanMQ's reliable message delivery, dead letter queues, and webhook-like interface to create robust microservice communications.

For more information about LeanMQ's capabilities:

- See the [LeanMQ Core API Reference](/reference/core) for details on queue management
- Explore the [Webhook API Reference](/reference/webhook) for the webhook-like interface
- Check the [Transactions Guide](/guide/advanced/transactions) for atomic operations across services
