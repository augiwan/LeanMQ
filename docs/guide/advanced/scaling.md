# Scaling LeanMQ

This guide covers strategies for scaling LeanMQ to handle high message volumes, improve throughput, and ensure reliability under load.

## Understanding Scaling Challenges

As your application grows, you'll face several scaling challenges:

1. **Message volume**: More messages being sent and processed
2. **Processing throughput**: Need to process messages faster
3. **Reliability under load**: Maintaining performance during traffic spikes
4. **Resource usage**: Efficient use of CPU, memory, and network resources
5. **Redis limitations**: Working within the constraints of Redis

## Vertical vs. Horizontal Scaling

LeanMQ supports both vertical and horizontal scaling approaches:

### Vertical Scaling

Vertical scaling involves adding more resources to a single instance:

- Using a more powerful Redis server
- Increasing memory allocation
- Running more worker threads in a single process

### Horizontal Scaling

Horizontal scaling involves distributing the load across multiple instances:

- Running multiple webhook service instances
- Using Redis Cluster for distributed storage
- Partitioning queues across different Redis instances

## Multi-Worker Processing

The simplest way to scale LeanMQ is to run multiple worker processes:

```python
import multiprocessing

def start_worker(worker_id):
    """Start a webhook worker process."""
    print(f"Starting worker {worker_id}")
    
    # Initialize webhook
    webhook = LeanMQWebhook(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        prefix="webhook:"  # Same prefix for all workers
    )
    
    # Register handlers
    @webhook.get("/order/status/")
    def process_order_status(data):
        print(f"Worker {worker_id} processing order {data['order_id']}")
        # Process the message...
    
    @webhook.get("/product/inventory/")
    def process_inventory_update(data):
        print(f"Worker {worker_id} processing product {data['product_id']}")
        # Process the message...
    
    # Start the service
    service = webhook.run_service()
    
    try:
        # Keep the worker alive
        while service.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"Worker {worker_id} shutting down...")
    finally:
        service.stop()
        webhook.close()

def main():
    """Start multiple worker processes."""
    # Determine number of workers based on CPU cores
    num_workers = max(2, multiprocessing.cpu_count())
    print(f"Starting {num_workers} worker processes")
    
    # Start worker processes
    processes = []
    for i in range(num_workers):
        process = multiprocessing.Process(target=start_worker, args=(i,))
        process.start()
        processes.append(process)
    
    # Wait for all processes to finish
    for process in processes:
        process.join()

if __name__ == "__main__":
    main()
```

### Using Consumer Groups

LeanMQ uses Redis Streams consumer groups to distribute work across multiple consumers:

- Each message is delivered to only one consumer
- Messages are tracked as pending until acknowledged
- Multiple consumers can work on different messages from the same queue

This ensures that messages are processed exactly once, even with multiple workers.

## Optimizing Message Processing

To improve processing throughput:

### Batch Processing

Process messages in batches for better efficiency:

```python
def process_messages_in_batches():
    """Process messages in batches for better throughput."""
    while True:
        # Get a batch of messages
        messages = queue.get_messages(count=100, block=True, timeout=1)
        
        if not messages:
            time.sleep(0.1)  # Avoid tight loop if no messages
            continue
        
        # Group messages by type for efficient processing
        messages_by_type = {}
        for message in messages:
            msg_type = message.data.get("type", "unknown")
            if msg_type not in messages_by_type:
                messages_by_type[msg_type] = []
            messages_by_type[msg_type].append(message)
        
        # Process each type in a batch
        for msg_type, msg_batch in messages_by_type.items():
            try:
                # Extract just the data for batch processing
                batch_data = [msg.data for msg in msg_batch]
                
                # Process the batch
                batch_process_by_type(msg_type, batch_data)
                
                # Acknowledge all successfully processed messages
                message_ids = [msg.id for msg in msg_batch]
                queue.acknowledge_messages(message_ids)
            except Exception as e:
                logger.error(f"Error processing batch of type {msg_type}: {e}")
                
                # Move failed batch to DLQ
                message_ids = [msg.id for msg in msg_batch]
                dlq = mq.get_dead_letter_queue(queue.name)
                queue.move_to_dlq(message_ids, str(e), dlq)
```

### Concurrent Processing

Use concurrent processing for CPU-bound or I/O-bound operations:

```python
from concurrent.futures import ThreadPoolExecutor

def process_messages_concurrently():
    """Process messages concurrently using a thread pool."""
    # Create thread pool
    with ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            # Get messages
            messages = queue.get_messages(count=20, block=True, timeout=1)
            
            if not messages:
                time.sleep(0.1)  # Avoid tight loop if no messages
                continue
            
            # Submit each message for processing in the thread pool
            futures = {
                executor.submit(process_message, message.data): message
                for message in messages
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(futures):
                message = futures[future]
                try:
                    # Get the result (or exception)
                    result = future.result()
                    
                    # Acknowledge successful processing
                    queue.acknowledge_messages([message.id])
                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {e}")
                    
                    # Move to DLQ
                    dlq = mq.get_dead_letter_queue(queue.name)
                    queue.move_to_dlq([message.id], str(e), dlq)
```

### Asynchronous Processing

For I/O-bound workloads, consider using asyncio:

```python
import asyncio

async def process_message_async(data):
    """Process a message asynchronously."""
    # Simulate async API call or database operation
    await asyncio.sleep(0.1)  # Replace with real async operation
    return {"processed": True, "id": data["id"]}

async def process_messages_async():
    """Process messages using asyncio for better I/O concurrency."""
    while True:
        # Get messages (note: this is still synchronous)
        messages = queue.get_messages(count=50, block=True, timeout=1)
        
        if not messages:
            await asyncio.sleep(0.1)  # Avoid tight loop if no messages
            continue
        
        # Process messages concurrently
        tasks = [process_message_async(message.data) for message in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        for message, result in zip(messages, results):
            if isinstance(result, Exception):
                logger.error(f"Error processing message {message.id}: {result}")
                
                # Move to DLQ
                dlq = mq.get_dead_letter_queue(queue.name)
                queue.move_to_dlq([message.id], str(result), dlq)
            else:
                # Acknowledge successful processing
                queue.acknowledge_messages([message.id])
```

## Queue Sharding and Partitioning

For very high volume applications, consider partitioning your queues:

### Functional Partitioning

Split queues by function or domain:

```python
# Create dedicated queues for different domains
orders_queue, _ = mq.create_queue_pair("orders")
inventory_queue, _ = mq.create_queue_pair("inventory")
users_queue, _ = mq.create_queue_pair("users")
payments_queue, _ = mq.create_queue_pair("payments")

# Use separate webhook instances for different domains
orders_webhook = LeanMQWebhook(prefix="orders:")
inventory_webhook = LeanMQWebhook(prefix="inventory:")
users_webhook = LeanMQWebhook(prefix="users:")
payments_webhook = LeanMQWebhook(prefix="payments:")

# Start separate services for each domain
orders_service = orders_webhook.run_service()
inventory_service = inventory_webhook.run_service()
users_service = users_webhook.run_service()
payments_service = payments_webhook.run_service()
```

### Sharding by Key

Partition data within a domain using consistent hashing:

```python
def get_shard_number(key, num_shards=4):
    """Get a consistent shard number for a key."""
    # Simple hashing function for demonstration
    hash_value = hash(key) 
    return abs(hash_value) % num_shards

def send_sharded_message(domain, key, data):
    """Send a message to the appropriate shard based on key."""
    shard = get_shard_number(key)
    queue_name = f"{domain}:shard{shard}"
    
    # Get or create the queue
    queue = mq.get_queue(queue_name)
    if not queue:
        queue, _ = mq.create_queue_pair(queue_name)
        
    # Send the message
    queue.send_message(data)
    
# Example usage
order_id = "ORD-12345"
shard = get_shard_number(order_id)
send_sharded_message("orders", order_id, {
    "order_id": order_id,
    "status": "shipped",
    "customer_id": "CUST-789"
})

# Process messages for a specific shard
def process_shard(domain, shard_num):
    queue_name = f"{domain}:shard{shard_num}"
    queue = mq.get_queue(queue_name)
    
    if not queue:
        logger.error(f"Queue {queue_name} not found")
        return
        
    while True:
        messages = queue.get_messages(count=10, block=True, timeout=1)
        # Process messages...
```

## Scaling Redis

As your application scales, you'll need to scale Redis as well:

### Redis Cluster

For very large deployments, use Redis Cluster:

```python
from redis.cluster import RedisCluster

# Connect to Redis Cluster
redis_nodes = [
    {"host": "redis-node1", "port": 6379},
    {"host": "redis-node2", "port": 6379},
    {"host": "redis-node3", "port": 6379}
]

# Note: This is an example of how you might connect to Redis Cluster
# LeanMQ would need to be extended to support Redis Cluster
redis_client = RedisCluster(startup_nodes=redis_nodes, decode_responses=True)

# Then use this client with LeanMQ
# (This would require extending LeanMQ to accept a custom Redis client)
```

### Redis Sentinel

For high availability, use Redis Sentinel:

```python
from redis.sentinel import Sentinel

# Connect to Redis Sentinel
sentinel = Sentinel([
    ('sentinel1', 26379),
    ('sentinel2', 26379),
    ('sentinel3', 26379)
], socket_timeout=0.1)

# Get the current master
master = sentinel.master_for('mymaster', socket_timeout=0.1)

# You'd need to extend LeanMQ to work with Sentinel
# Perhaps by creating a custom Redis client factory
```

## Load Balancing

For distributed setups, implement load balancing:

### Message Producers

Distribute message producers across multiple instances:

```python
# Load balanced producer pattern
class LoadBalancedProducer:
    """Send messages in a load-balanced way."""
    
    def __init__(self, redis_configs):
        """Initialize with multiple Redis configurations."""
        self.redis_clients = []
        for config in redis_configs:
            mq = LeanMQ(
                redis_host=config["host"],
                redis_port=config["port"],
                redis_db=config.get("db", 0),
                prefix=config.get("prefix", "")
            )
            self.redis_clients.append(mq)
        
    def send_message(self, queue_name, data):
        """Send a message using round-robin load balancing."""
        # Simple round-robin selection
        client_index = hash(str(data)) % len(self.redis_clients)
        client = self.redis_clients[client_index]
        
        # Get or create the queue
        queue = client.get_queue(queue_name)
        if not queue:
            queue, _ = client.create_queue_pair(queue_name)
            
        # Send the message
        return queue.send_message(data)
```

### Message Consumers

Implement adaptive consumers that scale based on load:

```python
import threading
import time

class AdaptiveConsumer:
    """Consumer that adapts to message volume."""
    
    def __init__(self, queue, min_workers=1, max_workers=10):
        """Initialize with queue and worker limits."""
        self.queue = queue
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.workers = []
        self.running = False
        self.stop_event = threading.Event()
        
    def start(self):
        """Start the adaptive consumer."""
        self.running = True
        
        # Start minimum number of workers
        for _ in range(self.min_workers):
            self._start_worker()
            
        # Start the scaling controller
        self.controller = threading.Thread(target=self._scaling_controller)
        self.controller.daemon = True
        self.controller.start()
        
    def stop(self):
        """Stop all workers and the controller."""
        self.running = False
        self.stop_event.set()
        
        # Wait for all workers to stop
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=5)
                
        # Wait for controller to stop
        if self.controller.is_alive():
            self.controller.join(timeout=5)
            
    def _start_worker(self):
        """Start a new worker thread."""
        worker = threading.Thread(target=self._worker_loop)
        worker.daemon = True
        worker.start()
        self.workers.append(worker)
        return worker
        
    def _worker_loop(self):
        """Worker thread that processes messages."""
        while self.running and not self.stop_event.is_set():
            try:
                # Get and process messages
                messages = self.queue.get_messages(count=10, block=True, timeout=1)
                
                if messages:
                    for message in messages:
                        # Process the message
                        try:
                            result = process_message(message.data)
                            self.queue.acknowledge_messages([message.id])
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            # Move to DLQ
                            dlq = mq.get_dead_letter_queue(self.queue.name)
                            self.queue.move_to_dlq([message.id], str(e), dlq)
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(1)
                
    def _scaling_controller(self):
        """Controller thread that adjusts worker count based on load."""
        while self.running and not self.stop_event.is_set():
            try:
                # Get queue information
                queue_info = self.queue.get_info()
                message_count = queue_info.message_count
                
                # Count active workers
                active_workers = sum(1 for w in self.workers if w.is_alive())
                
                # Scale up if needed
                if message_count > active_workers * 10 and active_workers < self.max_workers:
                    logger.info(f"Scaling up: {active_workers} -> {active_workers + 1}")
                    self._start_worker()
                    
                # Scale down if needed
                elif message_count < active_workers * 5 and active_workers > self.min_workers:
                    logger.info(f"Scaling down: {active_workers} -> {active_workers - 1}")
                    # Let one worker exit naturally by setting the stop event
                    # We'll clear it after one worker exits
                    self.stop_event.set()
                    time.sleep(2)  # Give a worker time to exit
                    self.stop_event.clear()
                    
                    # Remove exited workers from the list
                    self.workers = [w for w in self.workers if w.is_alive()]
                    
            except Exception as e:
                logger.error(f"Scaling controller error: {e}")
                
            # Check every few seconds
            time.sleep(5)
```

## Performance Tuning

Fine-tune various parameters for optimal performance:

### Message Batch Size

Find the optimal batch size for your workload:

```python
def find_optimal_batch_size():
    """Benchmark different batch sizes to find the optimal one."""
    batch_sizes = [1, 5, 10, 20, 50, 100, 200, 500]
    results = {}
    
    for batch_size in batch_sizes:
        start_time = time.time()
        total_processed = 0
        
        # Process messages in batches of the current size
        for _ in range(10):  # Run 10 iterations for each batch size
            messages = queue.get_messages(count=batch_size, block=False)
            if not messages:
                break
                
            # Process the messages
            for message in messages:
                process_message(message.data)
                queue.acknowledge_messages([message.id])
                total_processed += 1
                
        # Calculate throughput
        elapsed = time.time() - start_time
        if elapsed > 0 and total_processed > 0:
            throughput = total_processed / elapsed
            results[batch_size] = throughput
            print(f"Batch size {batch_size}: {throughput:.2f} messages/sec")
            
    # Find the best batch size
    best_batch_size = max(results.items(), key=lambda x: x[1])[0]
    print(f"Optimal batch size: {best_batch_size}")
    return best_batch_size
```

### Timeout and Polling Interval

Adjust timeouts and polling intervals:

```python
def optimize_polling_parameters():
    """Find optimal polling parameters."""
    # Different block timeouts to test
    timeouts = [0.1, 0.5, 1, 2, 5]
    results = {}
    
    for timeout in timeouts:
        start_time = time.time()
        total_processed = 0
        poll_count = 0
        
        # Run for a fixed time
        end_time = start_time + 30  # Run for 30 seconds
        
        while time.time() < end_time:
            messages = queue.get_messages(count=10, block=True, timeout=timeout)
            poll_count += 1
            
            if messages:
                # Process the messages
                for message in messages:
                    process_message(message.data)
                    queue.acknowledge_messages([message.id])
                    total_processed += 1
        
        # Calculate metrics
        elapsed = time.time() - start_time
        throughput = total_processed / elapsed if elapsed > 0 else 0
        polls_per_sec = poll_count / elapsed if elapsed > 0 else 0
        
        results[timeout] = {
            "throughput": throughput, 
            "polls_per_sec": polls_per_sec
        }
        
        print(f"Timeout {timeout}s: {throughput:.2f} msgs/sec, {polls_per_sec:.2f} polls/sec")
        
    # Find best balance between throughput and polling frequency
    # (This will depend on your specific workload characteristics)
    return results
```

## Monitoring Scaling Performance

Implement monitoring to track scaling performance:

```python
import time
import threading
import psutil

class PerformanceMonitor:
    """Monitor system and queue performance."""
    
    def __init__(self, mq, interval=10):
        """Initialize with LeanMQ instance and check interval."""
        self.mq = mq
        self.interval = interval
        self.running = False
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "queue_stats": {}
        }
        
    def start(self):
        """Start monitoring."""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=5)
            
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                self.metrics["cpu_usage"].append((time.time(), cpu_percent))
                self.metrics["memory_usage"].append((time.time(), memory_percent))
                
                # Collect queue metrics
                queues = self.mq.list_queues()
                for queue_info in queues:
                    name = queue_info.name
                    if name not in self.metrics["queue_stats"]:
                        self.metrics["queue_stats"][name] = []
                        
                    self.metrics["queue_stats"][name].append({
                        "timestamp": time.time(),
                        "message_count": queue_info.message_count,
                        "pending_messages": queue_info.pending_messages,
                        "is_dlq": queue_info.is_dlq
                    })
                    
                # Print current stats
                print(f"CPU: {cpu_percent}%, Memory: {memory_percent}%")
                for name, stats in self.metrics["queue_stats"].items():
                    if stats:
                        latest = stats[-1]
                        print(f"Queue {name}: {latest['message_count']} messages, "
                              f"{latest['pending_messages']} pending")
                              
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                
            # Sleep until next check
            time.sleep(self.interval)
            
    def get_metrics(self):
        """Get current metrics."""
        return self.metrics
        
    def reset_metrics(self):
        """Reset collected metrics."""
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "queue_stats": {}
        }
```

## Scaling Best Practices

### 1. Start simple, then scale

Begin with a single process and scale as needed:

```python
# Start with a simple setup
webhook = LeanMQWebhook()
service = webhook.run_service()

# Monitor performance
# If throughput becomes a bottleneck, add more workers
```

### 2. Implement proper monitoring

Always monitor your queues:

```python
# Check queue lengths regularly
def monitor_queue_lengths():
    while True:
        queues = mq.list_queues()
        for queue_info in queues:
            if queue_info.message_count > 1000:
                logger.warning(f"Queue {queue_info.name} is growing: {queue_info.message_count} messages")
                
        time.sleep(60)  # Check every minute
```

### 3. Plan for failure

Design your system to handle worker failures:

```python
# Implement heartbeats for workers
def worker_heartbeat(worker_id):
    """Send heartbeats to indicate worker is alive."""
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    
    while running:
        # Update heartbeat with current timestamp
        redis_client.setex(f"worker:{worker_id}:heartbeat", 60, time.time())
        time.sleep(10)
        
# Monitor worker heartbeats
def monitor_workers():
    """Check for stalled workers."""
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    
    while True:
        # Get all worker heartbeat keys
        worker_keys = redis_client.keys("worker:*:heartbeat")
        
        for key in worker_keys:
            worker_id = key.decode('utf-8').split(':')[1]
            
            # Check if heartbeat is recent
            last_beat = redis_client.get(key)
            if last_beat:
                last_beat_time = float(last_beat)
                now = time.time()
                
                if now - last_beat_time > 60:  # No heartbeat for 60 seconds
                    logger.warning(f"Worker {worker_id} appears to be stalled")
                    # Take corrective action like starting a replacement worker
                    
        time.sleep(30)  # Check every 30 seconds
```

### 4. Use queue TTL for time-sensitive messages

Set TTL for messages that become irrelevant after a period:

```python
# Send a message with TTL
queue.send_message(
    {
        "type": "price_update",
        "product_id": "PROD-123",
        "price": 99.99,
        "timestamp": time.time()
    },
    ttl_seconds=300  # Only relevant for 5 minutes
)

# Periodically process expired messages
def process_expired_messages_job():
    while True:
        expired_count = mq.process_expired_messages()
        if expired_count > 0:
            logger.info(f"Processed {expired_count} expired messages")
        time.sleep(60)  # Run every minute
```

## Next Steps

Now that you understand scaling strategies for LeanMQ, you can:

- Learn about [production deployment best practices](./production.md)
- Review [error handling strategies](./error-handling.md) for robust processing
- Explore the [WebhookService API reference](../../reference/webhook.md) for detailed configuration options

Remember that scaling is an ongoing process. Start with a simple setup, monitor performance, and scale incrementally as your needs grow.
