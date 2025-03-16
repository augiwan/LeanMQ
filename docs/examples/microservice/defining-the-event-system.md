# Microservice Communication Patterns

This example series demonstrates how to implement common microservice communication patterns using LeanMQ.

## Event-Driven Architecture

This example shows how to implement an event-driven architecture where services communicate by publishing and subscribing to events.

### Defining the Event System

```python
import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Type

from leanmq import LeanMQ


# Base Event class
class Event:
    """Base class for all events in the system."""
    
    def __init__(self, event_id: Optional[str] = None):
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = time.time()
        self.event_type = self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        event = cls(event_id=data.get("event_id"))
        event.timestamp = data.get("timestamp", time.time())
        return event


# Specific event types
class OrderCreatedEvent(Event):
    """Event fired when a new order is created."""
    
    def __init__(
        self,
        order_id: str,
        user_id: str,
        total: float,
        items: List[Dict[str, Any]],
        event_id: Optional[str] = None
    ):
        super().__init__(event_id)
        self.order_id = order_id
        self.user_id = user_id
        self.total = total
        self.items = items
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "order_id": self.order_id,
            "user_id": self.user_id,
            "total": self.total,
            "items": self.items
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderCreatedEvent":
        return cls(
            order_id=data.get("order_id", ""),
            user_id=data.get("user_id", ""),
            total=data.get("total", 0.0),
            items=data.get("items", []),
            event_id=data.get("event_id")
        )


class PaymentProcessedEvent(Event):
    """Event fired when a payment is processed."""
    
    def __init__(
        self,
        payment_id: str,
        order_id: str,
        amount: float,
        status: str,
        event_id: Optional[str] = None
    ):
        super().__init__(event_id)
        self.payment_id = payment_id
        self.order_id = order_id
        self.amount = amount
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "status": self.status
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaymentProcessedEvent":
        return cls(
            payment_id=data.get("payment_id", ""),
            order_id=data.get("order_id", ""),
            amount=data.get("amount", 0.0),
            status=data.get("status", ""),
            event_id=data.get("event_id")
        )


class OrderShippedEvent(Event):
    """Event fired when an order is shipped."""
    
    def __init__(
        self,
        order_id: str,
        tracking_number: str,
        carrier: str,
        event_id: Optional[str] = None
    ):
        super().__init__(event_id)
        self.order_id = order_id
        self.tracking_number = tracking_number
        self.carrier = carrier
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "order_id": self.order_id,
            "tracking_number": self.tracking_number,
            "carrier": self.carrier
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderShippedEvent":
        return cls(
            order_id=data.get("order_id", ""),
            tracking_number=data.get("tracking_number", ""),
            carrier=data.get("carrier", ""),
            event_id=data.get("event_id")
        )


# Registry of event types for deserialization
EVENT_TYPES = {
    "OrderCreatedEvent": OrderCreatedEvent,
    "PaymentProcessedEvent": PaymentProcessedEvent,
    "OrderShippedEvent": OrderShippedEvent
}


# Event serialization/deserialization
def serialize_event(event: Event) -> Dict[str, Any]:
    """Serialize an event to a dictionary."""
    return event.to_dict()


def deserialize_event(data: Dict[str, Any]) -> Optional[Event]:
    """Deserialize a dictionary to an event."""
    event_type = data.get("event_type")
    if not event_type or event_type not in EVENT_TYPES:
        return None
    
    event_class = EVENT_TYPES[event_type]
    return event_class.from_dict(data)
```

Continue to the [Event Bus Implementation](event-bus-implementation) section.
