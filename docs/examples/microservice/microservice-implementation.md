# Event-Driven Architecture (Continued)

## Microservice Implementation

```python
class Microservice:
    """Base class for microservices in the system."""
    
    def __init__(
        self,
        service_name: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        event_types: List[str] = None
    ):
        self.service_name = service_name
        
        # Initialize the event bus
        self.event_bus = EventBus(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db
        )
        
        # Subscribe to events
        self.subscription_queue_name = self.event_bus.subscribe(
            service_name,
            event_types
        )
        
        # Get the subscription queue
        self.mq = self.event_bus.mq
        self.subscription_queue = self.mq.get_queue(self.subscription_queue_name)
        self.subscription_dlq = self.mq.get_dead_letter_queue(self.subscription_queue_name)
        
        # Running state
        self.running = False
        self.event_thread = None
        
        # Logger
        self.logger = logging.getLogger(f"Service:{service_name}")
    
    def start(self):
        """Start the microservice."""
        if self.running:
            return
        
        # Start the event bus
        self.event_bus.start()
        
        # Start the event handler thread
        self.running = True
        self.event_thread = threading.Thread(target=self._handle_events)
        self.event_thread.daemon = True
        self.event_thread.start()
        
        self.logger.info(f"Microservice '{self.service_name}' started")
    
    def stop(self):
        """Stop the microservice."""
        if not self.running:
            return
        
        self.running = False
        
        if self.event_thread and self.event_thread.is_alive():
            self.event_thread.join(timeout=5)
        
        # Stop the event bus
        self.event_bus.stop()
        
        self.logger.info(f"Microservice '{self.service_name}' stopped")
    
    def close(self):
        """Close the microservice and release resources."""
        self.stop()
        self.event_bus.close()
    
    def publish_event(self, event: Event):
        """Publish an event.
        
        Args:
            event: Event to publish
        """
        self.event_bus.publish(event)
    
    def handle_event(self, event: Event):
        """Handle an incoming event.
        
        Args:
            event: Event to handle
            
        Returns:
            True if event was handled successfully, False otherwise
        """
        # Default implementation - subclasses should override
        self.logger.info(f"Received event: {event.event_type}")
        return True
    
    def _handle_events(self):
        """Process incoming events."""
        self.logger.info(f"Event handler started for '{self.service_name}'")
        
        while self.running:
            try:
                # Get events from the subscription queue
                messages = self.subscription_queue.get_messages(
                    count=5,
                    block_for_seconds=1
                )
                
                for message in messages:
                    try:
                        # Deserialize the event
                        event = deserialize_event(message.data)
                        
                        if not event:
                            self.logger.warning(f"Unknown event type: {message.data.get('event_type')}")
                            self.subscription_queue.acknowledge_messages([message.id])
                            continue
                        
                        # Handle the event
                        success = self.handle_event(event)
                        
                        # Acknowledge successful processing
                        if success:
                            self.subscription_queue.acknowledge_messages([message.id])
                        else:
                            # Move to DLQ if handling failed
                            self.subscription_queue.move_to_dlq(
                                [message.id],
                                "Event handling returned false",
                                self.subscription_dlq
                            )
                    
                    except Exception as e:
                        self.logger.error(f"Error handling event: {e}")
                        
                        # Move to DLQ
                        self.subscription_queue.move_to_dlq(
                            [message.id],
                            f"Handling error: {e}",
                            self.subscription_dlq
                        )
            
            except Exception as e:
                self.logger.error(f"Error in event handler: {e}")
                time.sleep(1)  # Avoid tight loop on persistent errors
        
        self.logger.info(f"Event handler stopped for '{self.service_name}'")
```

Continue to the [Implementing Specific Microservices](implementing-specific-microservices) section.
