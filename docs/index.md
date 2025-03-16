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

No need to configure <u>retries</u> or handle <u>rate limiting</u> &bull;
Failed webhooks automatically sent to a <u>dead letter queue</u> &bull;
You can set <u>TTL</u> to automatically expire old webhooks &bull;
<u>Atomic transactions</u> for when you need them &bull;
<u>Persisted</u> data so no more dropped webhooks
