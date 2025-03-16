# Webhook Services Examples

This page provides examples of how to use LeanMQ's webhook-like interface to create services for internal microservice communication.

## Basic Webhook Service

This example demonstrates a simple webhook service that processes messages in a background thread.

```python
import json
import time
from typing import Any, Dict

from leanmq import LeanMQWebhook


def main() -> None:
    """Run a basic webhook service example."""
    print("Starting webhook service example...")

    # Initialize the webhook client
    webhook = LeanMQWebhook(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        auto_start=False  # Don't start processing automatically
    )

    # Register webhook handlers
    @webhook.get("/order/status/")
    def process_order_status(data: Dict[str, Any]) -> None:
        """Process order status webhook."""
        print(f"Received order status webhook: {json.dumps(data, indent=2)}")
        # In a real service, this might update a database, send notifications, etc.

    @webhook.get("/product/inventory/")
    def process_inventory_update(data: Dict[str, Any]) -> None:
        """Process inventory update webhook."""
        print(f"Received inventory update webhook: {json.dumps(data, indent=2)}")
        # In a real service, this might update inventory counts, trigger reordering, etc.

    # Start the service with the new run_service() method
    service = webhook.run_service()

    # Send some test webhooks
    print("\nSending test webhooks...")

    # Send order status webhook
    webhook.send(
        "/order/status/",
        {"order_id": "ORD-12345", "status": "shipped", "updated_at": time.time()},
    )

    # Send inventory update webhook
    webhook.send(
        "/product/inventory/",
        {
            "product_id": "PROD-789",
            "name": "Wireless Headphones",
            "quantity": 150,
            "updated_at": time.time(),
        },
    )

    try:
        print("\nWebhook service is running. Press Ctrl+C to stop...")
        
        # Keep the main thread alive
        while service.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted, shutting down...")
    finally:
        # Stop the service
        service.stop()
        
        # Close the webhook connection
        webhook.close()

    print("Example finished")


if __name__ == "__main__":
    main()
```

## Advanced Webhook Service

This example shows a more advanced webhook service with custom error handling, retries, and multiple handler registration.

```python
import json
import logging
import signal
import threading
import time
from typing import Any, Dict, List, Optional

from leanmq import LeanMQ, LeanMQWebhook, WebhookService


class CustomWebhookService:
    """Enhanced webhook service with advanced features."""

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        log_level: int = logging.INFO,
    ) -> None:
        """Initialize the custom webhook service.
        
        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database
            log_level: Logging level
        """
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("CustomWebhookService")
        
        # Initialize webhook
        self.webhook = LeanMQWebhook(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            auto_start=False,
        )
        
        # Direct access to the LeanMQ instance for advanced operations
        self.mq = self.webhook.mq
        
        # Service state
        self.service = None
        self.running = False
        self.stats = {"processed": 0, "errors": 0, "last_error": None}
        
        # Register handlers
        self._register_handlers()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        # Monitoring thread
        self.monitor_thread = None

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle termination signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def _register_handlers(self) -> None:
        """Register webhook handlers."""
        
        @self.webhook.get("/order/status/")
        def handle_order_status(data: Dict[str, Any]) -> None:
            """Process order status updates."""
            try:
                order_id = data.get("order_id")
                status = data.get("status")
                
                if not order_id or not status:
                    raise ValueError("Missing required fields: order_id or status")
                
                self.logger.info(f"Processing order {order_id} status update: {status}")
                
                # Simulate database update
                self._update_order_in_db(order_id, status)
                
                # Simulate some business logic
                if status == "shipped":
                    self._send_shipping_notification(order_id)
                elif status == "delivered":
                    self._close_order(order_id)
                    
                self.stats["processed"] += 1
            except Exception as e:
                self.logger.error(f"Error processing order status: {e}")
                self.stats["errors"] += 1
                self.stats["last_error"] = str(e)
                raise  # Re-raise to move to DLQ

        @self.webhook.get("/product/inventory/")
        def handle_inventory_update(data: Dict[str, Any]) -> None:
            """Process inventory updates."""
            try:
                product_id = data.get("product_id")
                quantity = data.get("quantity")
                
                if not product_id or quantity is None:
                    raise ValueError("Missing required fields: product_id or quantity")
                
                self.logger.info(f"Processing inventory update for product {product_id}: {quantity}")
                
                # Simulate database update
                self._update_inventory_in_db(product_id, quantity)
                
                # Check inventory levels and take action if needed
                if quantity < 10:
                    self._trigger_restock_alert(product_id, quantity)
                    
                self.stats["processed"] += 1
            except Exception as e:
                self.logger.error(f"Error processing inventory update: {e}")
                self.stats["errors"] += 1
                self.stats["last_error"] = str(e)
                raise  # Re-raise to move to DLQ

    def _monitor_dlqs(self) -> None:
        """Monitor dead letter queues and log alerts."""
        while self.running:
            try:
                queues = self.mq.list_queues()
                
                for queue_info in queues:
                    if queue_info.is_dlq and queue_info.message_count > 0:
                        self.logger.warning(
                            f"DLQ {queue_info.name} has {queue_info.message_count} failed messages"
                        )
                        
                        # Check the most recent failed messages
                        dlq = self.mq.get_queue(queue_info.name)
                        if dlq:
                            failed_messages = dlq.get_messages(count=1)
                            for msg in failed_messages:
                                self.logger.warning(f"Sample failed message: {json.dumps(msg.data)}")
                                
                # Log service stats
                self.logger.info(f"Service stats: {json.dumps(self.stats)}")
                                
            except Exception as e:
                self.logger.error(f"Error monitoring DLQs: {e}")
                
            # Sleep for a while before checking again
            time.sleep(60)  # Check every minute

    def _update_order_in_db(self, order_id: str, status: str) -> None:
        """Simulate updating an order in the database.
        
        Args:
            order_id: Order ID
            status: New status
        """
        self.logger.debug(f"DB UPDATE: Set order {order_id} status to {status}")
        # In a real implementation, this would update a database

    def _send_shipping_notification(self, order_id: str) -> None:
        """Simulate sending a shipping notification.
        
        Args:
            order_id: Order ID
        """
        self.logger.debug(f"NOTIFICATION: Order {order_id} has shipped")
        # In a real implementation, this might send an email or push notification

    def _close_order(self, order_id: str) -> None:
        """Simulate closing an order.
        
        Args:
            order_id: Order ID
        """
        self.logger.debug(f"PROCESS: Closing order {order_id}")
        # In a real implementation, this might update multiple systems

    def _update_inventory_in_db(self, product_id: str, quantity: int) -> None:
        """Simulate updating inventory in the database.
        
        Args:
            product_id: Product ID
            quantity: New quantity
        """
        self.logger.debug(f"DB UPDATE: Set product {product_id} quantity to {quantity}")
        # In a real implementation, this would update a database

    def _trigger_restock_alert(self, product_id: str, quantity: int) -> None:
        """Simulate triggering a restock alert.
        
        Args:
            product_id: Product ID
            quantity: Current quantity
        """
        self.logger.debug(f"ALERT: Low inventory for product {product_id}: {quantity} remaining")
        # In a real implementation, this might create a purchase order

    def reprocess_failed_messages(self) -> int:
        """Reprocess messages from DLQs.
        
        Returns:
            Number of messages requeued
        """
        requeued_count = 0
        queues = self.mq.list_queues()
        
        for queue_info in queues:
            if queue_info.is_dlq and queue_info.message_count > 0:
                # Extract the original queue name from the DLQ name
                # DLQ names are in format: {prefix}{original_name}:dlq
                original_name = queue_info.name.rsplit(":dlq", 1)[0]
                
                # Get the queues
                dlq = self.mq.get_queue(queue_info.name)
                main_queue = self.mq.get_queue(original_name)
                
                if dlq and main_queue:
                    # Get messages from DLQ
                    failed_messages = dlq.get_messages(count=100)
                    message_ids = [msg.id for msg in failed_messages]
                    
                    if message_ids:
                        # Requeue messages
                        dlq.requeue_messages(message_ids, main_queue)
                        requeued_count += len(message_ids)
                        self.logger.info(
                            f"Requeued {len(message_ids)} messages from {queue_info.name} to {original_name}"
                        )
        
        return requeued_count

    def start(self) -> None:
        """Start the webhook service."""
        if self.running:
            self.logger.info("Service is already running")
            return
            
        self.running = True
        
        # Start the webhook service
        self.service = self.webhook.run_service(
            process_count=20,            # Process up to 20 messages per iteration
            block_for_seconds=1,         # Wait up to 1 second for new messages
            handle_signals=False,        # We handle signals ourselves
            log_level=logging.INFO,
        )
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_dlqs)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        self.logger.info("Custom webhook service started")

    def stop(self) -> None:
        """Stop the webhook service."""
        if not self.running:
            self.logger.info("Service is not running")
            return
            
        self.logger.info("Stopping custom webhook service...")
        self.running = False
        
        # Stop the webhook service
        if self.service:
            self.service.stop()
            
        # Wait for monitoring thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            
        # Close webhook connections
        self.webhook.close()
        
        self.logger.info("Custom webhook service stopped")

    def is_alive(self) -> bool:
        """Check if the service is running.
        
        Returns:
            True if the service is running
        """
        return self.running and (self.service and self.service.is_alive())


def main() -> None:
    """Run the advanced webhook service example."""
    # Create and start the service
    service = CustomWebhookService(log_level=logging.INFO)
    service.start()
    
    # Send some test webhooks
    print("\nSending test webhooks...")
    
    # Send order status webhooks
    service.webhook.send(
        "/order/status/",
        {"order_id": "ORD-12345", "status": "processing", "updated_at": time.time()},
    )
    
    time.sleep(1)  # Small delay to simulate time passing
    
    service.webhook.send(
        "/order/status/",
        {"order_id": "ORD-12345", "status": "shipped", "updated_at": time.time()},
    )
    
    # Send inventory update webhook
    service.webhook.send(
        "/product/inventory/",
        {
            "product_id": "PROD-789",
            "name": "Wireless Headphones",
            "quantity": 5,  # Low quantity to trigger alert
            "updated_at": time.time(),
        },
    )
    
    # Send a malformed webhook to demonstrate error handling
    service.webhook.send(
        "/product/inventory/",
        {
            "product_id": "PROD-999",
            # Missing quantity field to trigger validation error
            "updated_at": time.time(),
        },
    )
    
    try:
        print("\nAdvanced webhook service is running. Press Ctrl+C to stop...")
        
        # Keep the main thread alive for a while
        for _ in range(10):
            if not service.is_alive():
                break
            time.sleep(1)
            
        # Demonstrate reprocessing failed messages
        requeued = service.reprocess_failed_messages()
        print(f"\nRequeued {requeued} failed messages for reprocessing")
        
        # Allow some time for reprocessing
        time.sleep(3)
        
    except KeyboardInterrupt:
        print("Interrupted, shutting down...")
    finally:
        service.stop()
        
    print("Example finished")


if __name__ == "__main__":
    main()
```

## Scaling Webhook Services

This example demonstrates how to scale webhook processing across multiple processes or machines using consumer groups.

```python
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from typing import Any, Dict, List, Optional

from leanmq import LeanMQ, LeanMQWebhook


class ScalableWebhookWorker:
    """A scalable webhook worker that can run in multiple processes."""

    def __init__(
        self,
        worker_id: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        log_level: int = logging.INFO,
    ) -> None:
        """Initialize the scalable webhook worker.
        
        Args:
            worker_id: Unique identifier for this worker
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database
            log_level: Logging level
        """
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format=f"%(asctime)s - [Worker {worker_id}] - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(f"WebhookWorker-{worker_id}")
        
        self.worker_id = worker_id
        
        # Initialize webhook
        self.webhook = LeanMQWebhook(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            prefix=f"webhook:",  # Consistent prefix for all workers
            auto_start=False,
        )
        
        # Service state
        self.running = False
        self.worker_thread = None
        
        # Register handlers
        self._register_handlers()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle termination signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def _register_handlers(self) -> None:
        """Register webhook handlers."""
        
        @self.webhook.get("/order/status/")
        def handle_order_status(data: Dict[str, Any]) -> None:
            """Process order status updates."""
            order_id = data.get("order_id")
            status = data.get("status")
            
            self.logger.info(f"Worker {self.worker_id} processing order {order_id} status: {status}")
            
            # Simulate processing with variable duration
            processing_time = 0.5 + (hash(str(order_id)) % 10) / 10.0  # 0.5-1.5 seconds
            time.sleep(processing_time)
            
            self.logger.info(f"Worker {self.worker_id} completed processing order {order_id}")

        @self.webhook.get("/product/inventory/")
        def handle_inventory_update(data: Dict[str, Any]) -> None:
            """Process inventory updates."""
            product_id = data.get("product_id")
            quantity = data.get("quantity")
            
            self.logger.info(f"Worker {self.worker_id} processing inventory update for product {product_id}: {quantity}")
            
            # Simulate processing with variable duration
            processing_time = 0.3 + (hash(str(product_id)) % 10) / 10.0  # 0.3-1.3 seconds
            time.sleep(processing_time)
            
            self.logger.info(f"Worker {self.worker_id} completed processing product {product_id}")

    def _worker_loop(self) -> None:
        """Main worker loop processing webhooks."""
        self.logger.info(f"Worker {self.worker_id} started")
        
        while self.running:
            try:
                # Get consumer ID based on worker ID for better monitoring
                consumer_id = f"worker-{self.worker_id}"
                
                # Process webhooks
                processed = self.webhook.process_messages(
                    block=True,
                    timeout=1,
                    count=5,  # Process fewer messages per batch but more frequently
                )
                
                if processed > 0:
                    self.logger.debug(f"Worker {self.worker_id} processed {processed} webhook(s)")
            except Exception as e:
                self.logger.error(f"Error processing webhooks: {e}")
                time.sleep(1)  # Avoid tight loop in case of persistent errors

    def start(self) -> None:
        """Start the webhook worker."""
        if self.running:
            self.logger.info(f"Worker {self.worker_id} is already running")
            return
            
        self.running = True
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        self.logger.info(f"Worker {self.worker_id} started")

    def stop(self) -> None:
        """Stop the webhook worker."""
        if not self.running:
            self.logger.info(f"Worker {self.worker_id} is not running")
            return
            
        self.logger.info(f"Stopping worker {self.worker_id}...")
        self.running = False
        
        # Wait for worker thread to finish
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            
        # Close webhook connections
        self.webhook.close()
        
        self.logger.info(f"Worker {self.worker_id} stopped")

    def is_alive(self) -> bool:
        """Check if the worker is running.
        
        Returns:
            True if the worker is running
        """
        return self.running and bool(self.worker_thread and self.worker_thread.is_alive())


def start_workers(num_workers: int) -> List[ScalableWebhookWorker]:
    """Start multiple webhook workers.
    
    Args:
        num_workers: Number of workers to start
        
    Returns:
        List of started workers
    """
    workers = []
    
    for i in range(num_workers):
        # Create a worker with a unique ID
        worker_id = f"{socket.gethostname()}-{os.getpid()}-{i}"
        worker = ScalableWebhookWorker(worker_id=worker_id)
        worker.start()
        workers.append(worker)
        
    return workers


def send_test_webhooks(num_webhooks: int) -> None:
    """Send test webhooks to demonstrate load distribution.
    
    Args:
        num_webhooks: Number of webhooks to send
    """
    # Create a webhook client just for sending
    webhook = LeanMQWebhook(auto_start=False)
    
    print(f"\nSending {num_webhooks} test webhooks...")
    
    for i in range(num_webhooks):
        # Alternate between order status and inventory updates
        if i % 2 == 0:
            # Send order status webhook
            webhook.send(
                "/order/status/",
                {
                    "order_id": f"ORD-{10000 + i}",
                    "status": "processing" if i % 4 == 0 else "shipped",
                    "updated_at": time.time()
                },
            )
        else:
            # Send inventory update webhook
            webhook.send(
                "/product/inventory/",
                {
                    "product_id": f"PROD-{20000 + i}",
                    "name": f"Product {i}",
                    "quantity": 50 + (i % 100),
                    "updated_at": time.time()
                },
            )
    
    print(f"Sent {num_webhooks} webhooks")
    webhook.close()


def main() -> None:
    """Run the scalable webhook service example."""
    # Determine number of workers based on CPU cores
    num_workers = max(2, os.cpu_count() or 4)
    print(f"Starting {num_workers} webhook workers...")
    
    # Start the workers
    workers = start_workers(num_workers)
    
    try:
        # Give workers time to initialize
        time.sleep(2)
        
        # Send test webhooks to demonstrate load distribution
        send_test_webhooks(20)
        
        print("\nWorkers are processing webhooks. Press Ctrl+C to stop...")
        
        # Keep the main thread alive
        while any(worker.is_alive() for worker in workers):
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Interrupted, shutting down...")
    finally:
        # Stop all workers
        for worker in workers:
            worker.stop()
        
    print("Example finished")


if __name__ == "__main__":
    main()
```

## Next Steps

These examples demonstrate how to use LeanMQ's webhook functionality in various scenarios. For more information on specific aspects:

- See the [webhook pattern guide](../guide/webhook-pattern.md) for more details on how to use webhooks
- Explore [advanced queue management](../guide/advanced/queue-management.md) to learn about DLQs and other features
- Check the [webhook API reference](../reference/webhook.md) for complete documentation
