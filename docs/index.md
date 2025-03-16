---
# https://vitepress.dev/reference/default-theme-home-page
layout: CustomHome
sidebar: false

hero:
  name: "LeanMQ"
  tagline: "Replace your internal webhooks with a reliable, performant, and scalable MQ with a fantastic DX. "
  actions:
    - theme: brand
      text: Read the Guide
      link: /guide/intro

features:
  - title: Beautiful DX
    details: Its almost like your typical webhook. Try it with minimal changes, migrate when ready. Open source. Minimal dependencies.
    icon: 🧑‍💻
  - title: Efficient
    details: Make every CPU cycle and network request count. Stop wasting resources sending &amp; receiving webhooks.
    icon: 🚀
  - title: Feature packed
    details: Has everything you need to scale &mdash; dead letter queues, retries, persistence, TTL, and even atomic transactions!
    icon: 🎁
  - title: Powered by Redis Streams
    details: Built for scale, based on code that is used in production to power ~15M webhooks/month with the goal to handle 100M+ webhooks/month.
    icon: 🦸
---

```sh
pip install leanmq
```

```py
# from leanmq import LeanMQWebhook
webhook = LeanMQWebhook()
```

#### Sending a webhook is easy
```py
# Looks very similar to a POST request
webhook.send("/order/status/", {"id": "123", "status": "shipped"})
```

#### So is receiving them
```py
# Looks just like Flask, FastAPI, etc.
@webhook.get("/order/status/")
def process_order_status(data):
    print(f"Order: {data['id']}, status: {data['status']}")

# Process in a dedicated worker (or scale to 1000s)
webhook.run_service()

# Don't need dedicated workers? Schedule this in a CRON instead.
webhook.process_messages()

```

#### &hellip; and get all of these for free

Freedom from [retry handling](/guide/why-leanmq.md#the-problem-with-internal-webhooks) and [rate limiting](/guide/why-leanmq.md#the-problem-with-internal-webhooks) &bull;
Failed webhooks automatically go to a [dead letter queue](/guide/advanced/queue-management.md#dead-letter-queues-dlqs) &bull;
[Set a TTL](/guide/advanced/queue-management#message-time-to-live-ttl) to automatically expire old webhooks &bull;
[Persisted](/guide/why-leanmq.md#the-leanmq-solution) data so no more dropped webhooks &bull;
[Atomic transactions](/guide/advanced/transactions.md) for when you need them
