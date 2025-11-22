# Retry Mechanism Implementation Guide

## Overview

This document describes different approaches to implement retry mechanisms for failed crawl requests.

## Current Implementation

The worker uses a simple retry counter in message headers:
- Immediate requeue on failure
- Max 3 retries before moving to failed queue
- Works for transient errors but not rate limits

## Recommended: Delayed Retry with RabbitMQ TTL

### Architecture

```
crawl_requests → [FAIL] → retry_delay_30s → [TTL expires] → crawl_requests
                                                            ↓ [max retries]
                                                     crawl_requests_failed
```

### Implementation Steps

#### 1. Create Delay Queues

Update `src/worker.py` to declare delay queues with different TTLs:

```python
def connect(self):
    """Establish connection to RabbitMQ"""
    logger.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}")
    self.connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    self.channel = self.connection.channel()

    # Main queue
    self.channel.queue_declare(queue='crawl_requests', durable=True)
    self.channel.queue_declare(queue='raw_recipe_data', durable=True)
    self.channel.queue_declare(queue='crawl_requests_failed', durable=True)

    # Delay queues with TTL (30s, 5min, 1hour)
    # Messages expire and route back to main queue
    for delay_seconds in [30, 300, 3600]:
        self.channel.queue_declare(
            queue=f'crawl_requests_retry_{delay_seconds}s',
            durable=True,
            arguments={
                'x-message-ttl': delay_seconds * 1000,  # milliseconds
                'x-dead-letter-exchange': '',  # default exchange
                'x-dead-letter-routing-key': 'crawl_requests'  # back to main queue
            }
        )

    self.channel.basic_qos(prefetch_count=1)
    logger.info("Connected to RabbitMQ successfully")
```

#### 2. Update Error Handling

Replace immediate requeue with delayed retry:

```python
def process_message(self, ch, method, properties, body):
    """Process a single crawl request message"""
    instagram_url = "unknown"
    try:
        # ... existing processing code ...

    except InstagramRateLimitError as exc:
        # Rate limit - use longer delay
        retry_count = self._get_retry_count(properties)
        self._schedule_retry(body, properties, retry_count, delay='long')
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as exc:
        # Other errors - shorter delay
        retry_count = self._get_retry_count(properties)
        self._schedule_retry(body, properties, retry_count, delay='short')
        ch.basic_ack(delivery_tag=method.delivery_tag)

def _schedule_retry(self, body: bytes, properties, retry_count: int, delay: str = 'short'):
    """Schedule a delayed retry or move to failed queue"""
    max_retries = 3

    if retry_count >= max_retries:
        logger.error(f"❌ Max retries ({max_retries}) reached")
        self._move_to_failed_queue(body, "Max retries exceeded")
        return

    # Choose delay based on error type and retry count
    if delay == 'long':
        # Exponential backoff for rate limits: 5min, 15min, 1hour
        delay_seconds = [300, 900, 3600][min(retry_count, 2)]
    else:
        # Short delays for transient errors: 30s, 1min, 5min
        delay_seconds = [30, 60, 300][min(retry_count, 2)]

    retry_queue = f'crawl_requests_retry_{delay_seconds}s'

    # Increment retry count
    new_headers = properties.headers or {}
    new_headers['x-retry-count'] = retry_count + 1
    new_headers['x-first-attempt'] = new_headers.get('x-first-attempt', time.time())

    logger.info(f"🔄 Scheduling retry {retry_count + 1}/{max_retries} in {delay_seconds}s")

    # Publish to delay queue
    self.channel.basic_publish(
        exchange='',
        routing_key=retry_queue,
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json',
            headers=new_headers
        )
    )
```

### Advantages

✅ **True delayed retries** - Not instant requeue
✅ **Exponential backoff** - Longer delays for rate limits
✅ **No application logic needed** - RabbitMQ handles TTL
✅ **Observable** - Each delay queue visible in RabbitMQ UI
✅ **Flexible** - Different delays for different error types

### Disadvantages

⚠️ Requires multiple queues
⚠️ More complex RabbitMQ setup

## Alternative: Simple Time-Based Delay

Add delays in application code:

```python
except InstagramRateLimitError as exc:
    retry_count = self._get_retry_count(properties)

    if retry_count >= 3:
        self._move_to_failed_queue(body, str(exc))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    else:
        # Calculate exponential backoff
        delay = min(300 * (2 ** retry_count), 3600)  # Max 1 hour
        logger.warning(f"⚠️  Rate limit hit. Waiting {delay}s before retry...")

        # Sleep blocks the worker (not ideal for high throughput)
        time.sleep(delay)

        # Update headers and requeue
        new_headers = properties.headers or {}
        new_headers['x-retry-count'] = retry_count + 1

        self.channel.basic_publish(
            exchange='',
            routing_key='crawl_requests',
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                headers=new_headers
            )
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
```

### Advantages

✅ Simple to implement
✅ No additional queues needed

### Disadvantages

⚠️ Blocks the worker during sleep
⚠️ Not suitable for high-throughput scenarios
⚠️ Worker appears "hung" during delays

## Alternative: External Scheduler

Use a separate service to re-enqueue failed messages:

1. Store failed messages with retry timestamp in database or Redis
2. Separate cron job/scheduler checks for messages ready to retry
3. Re-publishes to main queue when delay expires

### Advantages

✅ Worker never blocks
✅ Centralized retry logic
✅ Can modify retry schedule without redeploying

### Disadvantages

⚠️ Requires additional infrastructure (DB/Redis)
⚠️ More complexity
⚠️ Requires separate scheduler process

## Monitoring & Observability

Regardless of approach, add metrics:

```python
# Track retry metrics
retry_metrics = {
    'total_retries': 0,
    'successful_retries': 0,
    'failed_retries': 0,
    'rate_limit_retries': 0
}

def _schedule_retry(self, ...):
    retry_metrics['total_retries'] += 1
    # ... rest of code

def process_message(self, ...):
    # On success after retry
    if retry_count > 0:
        retry_metrics['successful_retries'] += 1
```

Export metrics via:
- StatsD/Prometheus
- CloudWatch
- Application logs

## Recommendation

For Instagram scraper with rate limits:

**Use delayed retry with RabbitMQ TTL** because:
1. Rate limits require long delays (minutes/hours)
2. Worker shouldn't block on delays
3. Different error types need different delays
4. RabbitMQ handles the complexity

Implement with 3 delay levels:
- **30s**: Quick retry for network glitches
- **5min**: Rate limit initial cooldown
- **1hour**: Extended rate limit cooldown
