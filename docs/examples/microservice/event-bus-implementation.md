# Event-Driven Architecture (Continued)

## Event Bus Implementation

```python
class EventBus:
    """Central event bus for publishing and subscribing to events."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        prefix: str = "events:"
    ):
        # Initialize LeanMQ
        self.mq = LeanMQ(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            prefix=prefix
        )
        
        # Create main events queue
        self.events_queue, self.events_dlq = self.mq.create_queue_pair("all")
        
        # Map of event type to set of subscriber queues
        self.subscribers = {}
        
        # Logger
        self.logger = logging.getLogger("EventBus")
        
        # Running state
        self.running = False
        self.processor_thread = None
    
    def start(self):
        """Start the event bus processor."""
        if self.running:
            return
        
        self.running = True
        self.processor_thread = threading.Thread(target=self._process_events)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
        self.logger.info("Event bus started")
    
    def stop(self):
        """Stop the event bus processor."""
        if not self.running:
            return
        
        self.running = False
        
        if self.processor_thread and self.processor_thread.is_alive():
            self.processor_thread.join(timeout=5)
        
        self.logger.info("Event bus stopped")
    
    def close(self):
        """Close the event bus and release resources."""
        self.stop()
        self.mq.close()
    
    def publish(self, event: Event) -> str:
        """Publish an event to the event bus.
        
        Args:
            event: Event to publish
            
        Returns:
            Message ID of the published event
        """
        # Serialize the event
        event_data = serialize_event(event)
        
        # Publish to the events queue
        message_id = self.events_queue.send_message(event_data)
        
        self.logger.info(f"Published event: {event.event_type}, ID: {event.event_id}")
        
        return message_id
    
    def subscribe(self, service_name: str, event_types: List[str] = None) -> str:
        """Subscribe a service to specific event types.
        
        Args:
            service_name: Name of the subscribing service
            event_types: List of event types to subscribe to (None for all)
            
        Returns:
            Name of the subscription queue
        """
        # Create a subscription queue for this service
        queue_name = f"sub:{service_name}"
        queue, _ = self.mq.create_queue_pair(queue_name)
        
        # Register subscription
        for event_type in (event_types or EVENT_TYPES.keys()):
            if event_type not in self.subscribers:
                self.subscribers[event_type] = set()
            
            self.subscribers[event_type].add(queue_name)
        
        self.logger.info(f"Service '{service_name}' subscribed to events: {event_types or 'all'}")
        
        return queue_name
    
    def _process_events(self):
        """Process events from the main queue and distribute to subscribers."""
        self.logger.info("Event processor started")
        
        while self.running:
            try:
                # Get events from the main queue
                messages = self.events_queue.get_messages(
                    count=10,
                    block_for_seconds=1
                )
                
                for message in messages:
                    try:
                        # Deserialize the event
                        event_data = message.data
                        event = deserialize_event(event_data)
                        
                        if not event:
                            self.logger.warning(f"Unknown event type: {event_data.get('event_type')}")
                            continue
                        
                        # Get subscribers for this event type
                        event_type = event.event_type
                        subscriber_queues = self.subscribers.get(event_type, set())
                        
                        # Distribute to subscribers
                        for queue_name in subscriber_queues:
                            try:
                                subscriber_queue = self.mq.get_queue(queue_name)
                                if subscriber_queue:
                                    subscriber_queue.send_message(event_data)
                            except Exception as e:
                                self.logger.error(f"Error distributing to {queue_name}: {e}")
                        
                        # Acknowledge the event
                        self.events_queue.acknowledge_messages([message.id])
                        
                    except Exception as e:
                        self.logger.error(f"Error processing event {message.id}: {e}")
                        
                        # Move to DLQ
                        self.events_queue.move_to_dlq(
                            [message.id],
                            f"Processing error: {e}",
                            self.events_dlq
                        )
            
            except Exception as e:
                self.logger.error(f"Error in event processor: {e}")
                time.sleep(1)  # Avoid tight loop on persistent errors
        
        self.logger.info("Event processor stopped")
```

Continue to the [Microservice Implementation](microservice-implementation) section.
