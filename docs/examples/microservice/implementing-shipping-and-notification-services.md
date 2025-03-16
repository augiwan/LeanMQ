# Event-Driven Architecture (Continued)

## Implementing Specific Microservices (Continued)

### Shipping Service

```python
class ShippingService(Microservice):
    """Service for handling shipping."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        super().__init__(
            service_name="shipping-service",
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            event_types=["PaymentProcessedEvent"]
        )
        
        # In-memory shipment storage (for demonstration)
        self.shipments = {}
    
    def handle_event(self, event: Event) -> bool:
        """Handle incoming events.
        
        Args:
            event: Event to handle
            
        Returns:
            True if handled successfully
        """
        if isinstance(event, PaymentProcessedEvent):
            return self._handle_payment_processed(event)
        
        return False
    
    def _handle_payment_processed(self, event: PaymentProcessedEvent) -> bool:
        """Handle payment processed event.
        
        Args:
            event: Payment processed event
            
        Returns:
            True if handled successfully
        """
        # Only create shipments for successful payments
        if event.status != "succeeded":
            self.logger.info(f"Skipping shipment for failed payment on order {event.order_id}")
            return True
        
        order_id = event.order_id
        
        # Generate shipment details
        tracking_number = f"TRACK-{uuid.uuid4().hex[:8].upper()}"
        carriers = ["FedEx", "UPS", "USPS", "DHL"]
        carrier = carriers[uuid.uuid4().int % len(carriers)]
        
        # In a real service, this would integrate with shipping providers
        self.logger.info(f"Creating shipment for order {order_id}")
        
        # Simulate shipping processing
        time.sleep(2)
        
        # Store shipment information
        shipment = {
            "order_id": order_id,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "status": "shipped",
            "created_at": time.time()
        }
        
        self.shipments[order_id] = shipment
        
        # Publish order shipped event
        event = OrderShippedEvent(
            order_id=order_id,
            tracking_number=tracking_number,
            carrier=carrier
        )
        
        self.publish_event(event)
        
        self.logger.info(f"Order {order_id} shipped with {carrier}, tracking: {tracking_number}")
        
        return True
```

### Notification Service

```python
class NotificationService(Microservice):
    """Service for sending notifications."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        super().__init__(
            service_name="notification-service",
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            # Subscribe to all event types
            event_types=None
        )
    
    def handle_event(self, event: Event) -> bool:
        """Handle all events by sending appropriate notifications.
        
        Args:
            event: Event to handle
            
        Returns:
            True if handled successfully
        """
        if isinstance(event, OrderCreatedEvent):
            self._send_notification(
                user_id=event.user_id,
                subject="Order Confirmation",
                message=f"Your order #{event.order_id} has been received. "
                        f"Total: ${event.total:.2f}"
            )
        
        elif isinstance(event, PaymentProcessedEvent):
            if event.status == "succeeded":
                self._send_notification(
                    order_id=event.order_id,
                    subject="Payment Confirmation",
                    message=f"Your payment of ${event.amount:.2f} for order "
                            f"#{event.order_id} has been processed."
                )
            else:
                self._send_notification(
                    order_id=event.order_id,
                    subject="Payment Failed",
                    message=f"Your payment for order #{event.order_id} has failed. "
                            f"Please update your payment information."
                )
        
        elif isinstance(event, OrderShippedEvent):
            self._send_notification(
                order_id=event.order_id,
                subject="Order Shipped",
                message=f"Your order #{event.order_id} has been shipped with "
                        f"{event.carrier}. Tracking number: {event.tracking_number}"
            )
        
        return True
    
    def _send_notification(self, subject: str, message: str, user_id: str = None, order_id: str = None):
        """Send a notification (simulated).
        
        Args:
            subject: Notification subject
            message: Notification message
            user_id: User ID (optional)
            order_id: Order ID (optional)
        """
        # In a real service, this would send emails, SMS, push notifications, etc.
        # For demonstration, we'll just log the notification
        recipient = f"user {user_id}" if user_id else f"order {order_id}"
        self.logger.info(f"Sending notification to {recipient}:")
        self.logger.info(f"  Subject: {subject}")
        self.logger.info(f"  Message: {message}")
```

Continue to the [Running the Event-Driven System](running-the-event-driven-system) section.
