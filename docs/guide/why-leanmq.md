# Why LeanMQ?

## The Problem with Internal Webhooks

If you're building a microservice architecture, you've likely encountered these challenges with traditional internal webhooks:

- **Message loss**: When a service is down, webhooks can be lost forever
- **Retry complexity**: Building robust retry mechanisms is difficult and error-prone
- **Scalability issues**: As your system grows, managing webhook reliability becomes increasingly complex
- **Monitoring blindspots**: Hard to track failed or delayed webhooks

## The LeanMQ Solution

LeanMQ addresses these problems by providing:

- **Persistent message storage**: Messages are stored in Redis until successfully processed
- **Dead letter queues**: Failed messages are automatically moved to DLQs for inspection and reprocessing
- **Simple retry mechanisms**: Built-in support for tracking delivery attempts
- **Familiar webhook-like API**: Use decorators similar to web frameworks

Best of all, you can adopt LeanMQ with minimal changes to your existing code.

## Key Features

- **Dead Letter Queues**: Automatically capture and isolate failed messages
- **Message Time-to-Live (TTL)**: Set expiration times for messages
- **Atomic Transactions**: Ensure all-or-nothing operations across multiple queues
- **Consumer Groups**: Distribute message processing across multiple workers
- **Message Retry Tracking**: Monitor delivery attempts for better reliability
- **Webhook-like Pattern**: Familiar API for service-to-service communication

## When to Use LeanMQ

LeanMQ is ideal for:

- **Internal service communication**: Replace HTTP-based internal webhooks
- **Event-driven architectures**: Reliable event propagation between services
- **Task processing**: Distribute work across multiple services
- **Decoupling systems**: Reduce direct dependencies between components

It's particularly valuable when:
- You need higher reliability than HTTP webhooks provide
- You want to decouple services for better scalability
- You're already using Redis in your infrastructure
- You want simplicity without the operational complexity of larger message brokers
