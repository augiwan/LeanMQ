# LeanMQ

[![GitHub Repo stars](https://img.shields.io/github/stars/augiwan/LeanMQ?style=social)](https://github.com/augiwan/LeanMQ/stargazers)
[![GitHub license](https://img.shields.io/github/license/augiwan/leanmq)](https://github.com/augiwan/LeanMQ/blob/main/LICENSE)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/LeanMQ)](https://pypi.org/project/LeanMQ/)
[![Python Version](https://img.shields.io/pypi/pyversions/LeanMQ)](https://pypi.org/project/LeanMQ/)
[![PyPI](https://img.shields.io/pypi/v/LeanMQ)](https://pypi.org/project/LeanMQ/)
[![PyPI - Status](https://img.shields.io/pypi/status/leanmq)](https://pypi.org/project/leanmq/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-Ruff-261230.svg)](https://github.com/astral-sh/ruff)
![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)

<hr />

### 🔥 Just getting started – show your support!
> If you find LeanMQ interesting, consider giving it a ⭐ star on GitHub!  
> It helps others discover it and motivates ongoing improvements.

<hr />

LeanMQ is a lightweight, message queue library with minimal dependencies for internal or async microservice communication. It provides a simple but powerful implementation using Redis Streams with support for &mdash;

- **Dead Letter Queues**: Automatic handling of failed messages
- **Message TTL**: Set expiration times for messages
- **Atomic Transactions**: Send multiple messages in a single transaction
- **Consumer Groups**: Support for multiple consumers
- **Message Tracking**: Track delivery attempts and failures

#### [Read the docs](https://leanmq.augiwan.com)

<hr />

## Installation

```bash
pip install leanmq
```

## Quick Start

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

Find rest of the docs [here](https://leanmq.augiwan.com).

## License

Apache 2.0 - see LICENSE.md for details.

## Copyright

Copyright (c) 2025 Augustus D'Souza
