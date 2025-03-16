# Event-Driven Architecture (Continued)

## Implementing Specific Microservices

### Order Service

```python
class OrderService(Microservice):
    """Service for managing orders."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        super().__init__(
            service_name="order-service",
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            event_types=["PaymentProcessedEvent", "OrderShippedEvent"]
        )
        
        # In-memory order storage (for demonstration)
        self.orders = {}
    
    def create_order(self, user_id: str, items: List[Dict[str, Any]]) -> str:
        """Create a new order.
        
        Args:
            user_id: User identifier
            items: List of order items
            
        Returns:
            Order identifier
        """
        # Generate order ID
        order_id = f"order-{uuid.uuid4()}"
        
        # Calculate total
        total = sum(item.get("price", 0) * item.get("quantity", 0) for item in items)
        
        # Create order
        order = {
            "order_id": order_id,
            "user_id": user_id,
            "items": items,
            "total": total,
            "status": "created",
            "created_at": time.time()
        }
        
        # Store order
        self.orders[order_id] = order
        
        # Publish event
        event = OrderCreatedEvent(
            order_id=order_id,
            user_id=user_id,
            total=total,
            items=items
        )
        
        self.publish_event(event)
        
        self.logger.info(f"Created order {order_id} for user {user_id}")
        
        return order_id
    
    def handle_event(self, event: Event) -> bool:
        """Handle incoming events.
        
        Args:
            event: Event to handle
            
        Returns:
            True if handled successfully
        """
        if isinstance(event, PaymentProcessedEvent):
            return self._handle_payment_processed(event)
        elif isinstance(event, OrderShippedEvent):
            return self._handle_order_shipped(event)
        
        return False
    
    def _handle_payment_processed(self, event: PaymentProcessedEvent) -> bool:
        """Handle payment processed event.
        
        Args:
            event: Payment processed event
            
        Returns:
            True if handled successfully
        """
        order_id = event.order_id
        status = event.status
        
        # Update order status based on payment result
        if order_id in self.orders:
            order = self.orders[order_id]
            
            if status == "succeeded":
                order["status"] = "paid"
                self.logger.info(f"Order {order_id} marked as paid")
            else:
                order["status"] = "payment_failed"
                self.logger.warning(f"Payment failed for order {order_id}")
            
            order["payment_id"] = event.payment_id
            order["updated_at"] = time.time()
            
            return True
        else:
            self.logger.error(f"Order {order_id} not found for payment {event.payment_id}")
            return False
    
    def _handle_order_shipped(self, event: OrderShippedEvent) -> bool:
        """Handle order shipped event.
        
        Args:
            event: Order shipped event
            
        Returns:
            True if handled successfully
        """
        order_id = event.order_id
        
        # Update order status
        if order_id in self.orders:
            order = self.orders[order_id]
            
            order["status"] = "shipped"
            order["tracking_number"] = event.tracking_number
            order["carrier"] = event.carrier
            order["shipped_at"] = time.time()
            
            self.logger.info(f"Order {order_id} marked as shipped")
            
            return True
        else:
            self.logger.error(f"Order {order_id} not found for shipping update")
            return False
```

### Payment Service

```python
class PaymentService(Microservice):
    """Service for processing payments."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        super().__init__(
            service_name="payment-service",
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            event_types=["OrderCreatedEvent"]
        )
        
        # In-memory payment storage (for demonstration)
        self.payments = {}
    
    def handle_event(self, event: Event) -> bool:
        """Handle incoming events.
        
        Args:
            event: Event to handle
            
        Returns:
            True if handled successfully
        """
        if isinstance(event, OrderCreatedEvent):
            return self._handle_order_created(event)
        
        return False
    
    def _handle_order_created(self, event: OrderCreatedEvent) -> bool:
        """Handle order created event by processing payment.
        
        Args:
            event: Order created event
            
        Returns:
            True if handled successfully
        """
        order_id = event.order_id
        amount = event.total
        
        # Generate payment ID
        payment_id = f"payment-{uuid.uuid4()}"
        
        # In a real service, this would integrate with a payment provider
        # For demonstration, we'll simulate a payment
        self.logger.info(f"Processing payment for order {order_id}, amount: ${amount:.2f}")
        
        # Simulate payment processing
        time.sleep(1.5)
        
        # Simulate success (with occasional failures)
        success = uuid.uuid4().int % 10 != 0  # 90% success rate
        
        status = "succeeded" if success else "failed"
        
        # Store payment information
        payment = {
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": amount,
            "status": status,
            "created_at": time.time()
        }
        
        self.payments[payment_id] = payment
        
        # Publish payment processed event
        event = PaymentProcessedEvent(
            payment_id=payment_id,
            order_id=order_id,
            amount=amount,
            status=status
        )
        
        self.publish_event(event)
        
        self.logger.info(f"Payment {payment_id} {status} for order {order_id}")
        
        return True
```

Continue to the [Shipping and Notification Services](./implementing-shipping-and-notification-services.md) section.
