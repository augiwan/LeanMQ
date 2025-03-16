# Getting Started with LeanMQ

This guide will walk you through the basics of setting up and using LeanMQ in your projects. We'll cover installation, basic configuration, and how to send and receive messages.

## Installation

```bash
pip install leanmq
```

LeanMQ requires a Redis server (version 5.0 or higher) for storing messages. If you don't already have Redis running, you can:

- Install Redis locally: [Redis installation guide](https://redis.io/topics/quickstart)
- Use Docker:
  ```bash
  docker run --name redis -p 6379:6379 -d redis
  ```
- Use a managed Redis service like Redis Cloud, AWS ElastiCache, or similar

### Quick Example

Here's a taste of how simple it is to use LeanMQ with its webhook-like pattern:

```python
# Set up a webhook server
from leanmq import LeanMQWebhook

webhook = LeanMQWebhook()

# Register a handler
@webhook.get("/order/status/")
def process_order_status(data):
    print(f"Order {data['order_id']} status: {data['status']}")

# Start processing webhooks in a background thread
service = webhook.run_service()

# In another service, send a webhook
webhook.send("/order/status/", {
    "order_id": "ORD-12345", 
    "status": "shipped"
})
```

## Next Steps

Now that you understand the basics, you can:

- Get a [basic overview](./basic-overview.md) of LeanMQ
- Learn about the [webhook pattern](./webhook-pattern.md) in more detail
- Explore [advanced queue management](./advanced/queue-management.md)
- See how to implement [transactions](./advanced/transactions.md) for atomic operations
- Check out complete [example applications](../examples/basic-messaging.md)

For a comprehensive reference of all classes and methods, visit the [API Reference](../reference/core.md) section.
