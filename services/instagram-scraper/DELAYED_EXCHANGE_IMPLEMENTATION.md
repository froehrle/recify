# Delayed Exchange Implementation ✅

## What is This?

This project uses **RabbitMQ's Delayed Message Exchange Plugin** to automatically retry failed Instagram scraping requests after a configurable delay.

Think of it like this: When a request fails (e.g., Instagram rate limit), instead of retrying immediately, we tell RabbitMQ "hold onto this message and give it back to me in 5 minutes." The worker doesn't have to wait around - it can process other messages while RabbitMQ handles the timing.

## Understanding RabbitMQ Basics

### What is RabbitMQ?

RabbitMQ is a **message broker** - it receives messages from producers and delivers them to consumers. It's like a post office for your applications.

**Key concepts:**
- **Queue**: A waiting line for messages (like a mailbox)
- **Exchange**: Routes messages to queues (like a sorting office)
- **Message**: Data being sent (like a letter)
- **Producer**: Sends messages (sender)
- **Consumer**: Receives messages (receiver)

### Normal Message Flow

```
Producer → Exchange → Queue → Consumer
```

### Our Queue Structure

We have **3 queues**:

1. **crawl_requests** - New Instagram URLs to scrape
2. **raw_recipe_data** - Successfully scraped data
3. **crawl_requests_failed** - Messages that failed after 3 retries

We have **1 special exchange**:

- **delayed_exchange** - Holds messages temporarily before delivering them

## How Delayed Messages Work

### The Problem

When Instagram rate limits us (HTTP 401/403), retrying immediately will just fail again. We need to wait before retrying.

### Traditional Approach (We Don't Use This)

Most systems would make the worker wait:

```python
# ❌ Bad: Worker blocks while waiting
time.sleep(300)  # Wait 5 minutes
retry()
```

**Problem:** The worker can't do anything else for 5 minutes!

### Our Approach: Delayed Exchange

Instead, we use RabbitMQ's delayed exchange plugin:

```python
# ✅ Good: Worker keeps working
publish_to_delayed_exchange(message, delay=300_seconds)
# Worker immediately moves to next message
```

**Benefit:** The worker never waits - RabbitMQ handles the timing!

## How the Delayed Exchange Works

### 1. Message Flow Diagram

```
┌──────────────┐
│   Worker     │
│  (Consumer)  │
└──────────────┘
       ▲
       │ 3. Delivers message after delay
       │
┌─────────────────┐
│ crawl_requests  │ ◄─── Main queue
└─────────────────┘
       ▲
       │
       │ 2. Routes here when delay expires
       │
┌──────────────────────┐
│ delayed_exchange     │ ◄─── Special exchange that holds messages
│ (x-delayed-message)  │      Each message has individual delay
└──────────────────────┘
       ▲
       │
       │ 1. Worker publishes here when retry needed
       │
┌──────────────┐
│   Worker     │
│  (Producer)  │
└──────────────┘
```

### 2. Step-by-Step Process

**When a message fails:**

1. **Worker detects error** (e.g., Instagram rate limit)
2. **Worker calculates delay** (e.g., 5 minutes)
3. **Worker publishes to delayed_exchange** with header `x-delay: 300000` (milliseconds)
4. **delayed_exchange receives message** and starts internal timer
5. **Worker immediately continues** processing other messages
6. **After 5 minutes pass**, delayed_exchange automatically routes message to `crawl_requests`
7. **Worker picks up message** from `crawl_requests` and retries

**The key:** Steps 5 and 6 happen in parallel - worker doesn't wait!

### 3. The Magic: x-delay Header

The delayed exchange looks for a special header called `x-delay` in each message:

```python
headers = {
    'x-delay': 300000,  # Delay in milliseconds (5 minutes)
    'x-retry-count': 1,
    'x-last-error': 'Instagram rate limit: 401'
}
```

Each message can have a **different delay**:
- Message A: Wait 30 seconds
- Message B: Wait 5 minutes
- Message C: Wait 1 hour

This is more flexible than having separate queues for each delay time.

### 4. Exchange Type: x-delayed-message

The `delayed_exchange` is a special type called **x-delayed-message**:

```python
self.channel.exchange_declare(
    exchange='delayed_exchange',
    exchange_type='x-delayed-message',  # Special plugin type
    arguments={'x-delayed-type': 'direct'},  # Routing behavior
    durable=True  # Survives RabbitMQ restart
)
```

**What does this do?**
- `exchange_type='x-delayed-message'`: Enables delay functionality (from plugin)
- `x-delayed-type='direct'`: After delay, route message directly to bound queue
- `durable=True`: Exchange persists if RabbitMQ restarts

## Real-World Example

Let's walk through a complete retry scenario:

### Scenario: Instagram Rate Limit

**10:00:00** - Worker receives URL to scrape
```
Message: {"instagram_url": "https://instagram.com/p/ABC123/"}
```

**10:00:01** - Worker tries to scrape, gets rate limited (401)
```
Error: Instagram rate limit
Retry count: 0 (first attempt)
```

**10:00:01** - Worker calculates delay and publishes to delayed_exchange
```python
delay_ms = 300000  # 5 minutes for rate limit
headers = {'x-delay': 300000, 'x-retry-count': 1}

channel.basic_publish(
    exchange='delayed_exchange',
    routing_key='crawl_requests',
    body=message,
    properties=pika.BasicProperties(headers=headers)
)
```

**10:00:01** - Message sits in delayed_exchange
```
Worker log: "🔄 Scheduling retry 1/3 in 5m (using delayed exchange)"
Worker continues processing other messages...
```

**10:05:01** - Delay expires, message routes to crawl_requests
```
delayed_exchange → crawl_requests (automatic)
```

**10:05:01** - Worker picks up message and retries
```
Worker processes message again
If still rate limited → Retry 2 with 15 minute delay
If successful → Publish to raw_recipe_data
```

### Timeline Visualization

```
10:00:00  ┌──────┐
          │ Fail │ (401 error)
          └──────┘
             │
             ▼
10:00:01  ┌──────────────────────┐
          │ delayed_exchange     │ (holds message for 5 min)
          │ x-delay: 300000ms    │
          └──────────────────────┘
             │
             │ Worker processes
             │ OTHER messages
             │ during this time
             ▼
10:05:01  ┌─────────────────┐
          │ crawl_requests  │ (message auto-routed here)
          └─────────────────┘
             │
             ▼
          ┌──────┐
          │ Retry│
          └──────┘
```

## Implementation Details

### 1. RabbitMQ Plugin

**File:** `/rabbitmq/Dockerfile`

```dockerfile
FROM rabbitmq:3.11-management

# Download and install the delayed message exchange plugin
RUN apt-get update && \
    apt-get install -y curl && \
    curl -L https://github.com/rabbitmq/rabbitmq-delayed-message-exchange/releases/download/3.11.1/rabbitmq_delayed_message_exchange-3.11.1.ez \
        -o /opt/rabbitmq/plugins/rabbitmq_delayed_message_exchange-3.11.1.ez && \
    rabbitmq-plugins enable --offline rabbitmq_delayed_message_exchange && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### 2. Docker Compose

**File:** `/docker-compose.yml`

```yaml
rabbitmq:
  build: ./rabbitmq  # Custom image with plugin
  container_name: instagram-rabbitmq
  # ... rest of config
```

### 3. Worker Code

**File:** `src/worker.py`

#### Exchange Declaration
```python
# Declare delayed message exchange
self.channel.exchange_declare(
    exchange='delayed_exchange',
    exchange_type='x-delayed-message',
    arguments={'x-delayed-type': 'direct'},
    durable=True
)

# Bind main queue to delayed exchange
self.channel.queue_bind(
    queue='crawl_requests',
    exchange='delayed_exchange',
    routing_key='crawl_requests'
)
```

#### Retry Scheduling
```python
def _schedule_retry(self, body, properties, retry_count, delay_type='short', error=''):
    # Calculate delay in milliseconds
    if delay_type == 'long':
        delay_ms = [300000, 900000, 3600000][min(retry_count, 2)]  # 5m, 15m, 1h
    else:
        delay_ms = [30000, 300000, 900000][min(retry_count, 2)]    # 30s, 5m, 15m

    # Set delay in message header
    new_headers = properties.headers or {}
    new_headers['x-delay'] = delay_ms
    new_headers['x-retry-count'] = retry_count + 1

    # Publish to delayed exchange
    self.channel.basic_publish(
        exchange='delayed_exchange',
        routing_key='crawl_requests',
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=2,
            headers=new_headers
        )
    )
```

## Retry Strategy

**Rate Limit Errors (401/403):**
```
Attempt 1 → x-delay: 300000ms (5 min)   → Retry
Attempt 2 → x-delay: 900000ms (15 min)  → Retry
Attempt 3 → x-delay: 3600000ms (1 hour) → Retry
Attempt 4 → Move to failed queue
```

**Other Errors:**
```
Attempt 1 → x-delay: 30000ms (30 sec)   → Retry
Attempt 2 → x-delay: 300000ms (5 min)   → Retry
Attempt 3 → x-delay: 900000ms (15 min)  → Retry
Attempt 4 → Move to failed queue
```

## How It Works

1. **Message fails** → Worker catches error
2. **Calculate delay** → Based on retry count and error type
3. **Publish to delayed_exchange** → With `x-delay` header in milliseconds
4. **Exchange holds message** → For the specified delay
5. **After delay expires** → Exchange routes to `crawl_requests`
6. **Worker retries** → Picks up message from main queue
7. **Repeat** → Up to 3 times, then move to failed queue

## Why Use Delayed Exchange?

### Benefits

✅ **Worker efficiency** - Worker never waits, processes other messages during delays
✅ **Flexible delays** - Each message can have any delay time (not limited to predefined values)
✅ **Automatic retry** - RabbitMQ handles all timing, no manual timers in code
✅ **Exponential backoff** - Longer delays for repeated failures (5min → 15min → 1hour)
✅ **Observable** - See delayed messages in RabbitMQ Management UI
✅ **Reliable** - Messages persist even if RabbitMQ restarts
✅ **Simple code** - Just set `x-delay` header, RabbitMQ does the rest

### Common Use Cases

This pattern is useful whenever you need to retry something later:

- **Rate limiting** - Wait before retrying API calls
- **Exponential backoff** - Retry with increasing delays
- **Scheduled tasks** - Do something in X minutes
- **Cooldown periods** - Wait between operations
- **Circuit breaker** - Temporarily stop retrying failing service

## Monitoring

### Check Exchange
```bash
# List exchanges
docker exec instagram-rabbitmq rabbitmqctl list_exchanges name type

# Should see:
# delayed_exchange    x-delayed-message
```

### Check Queues
```bash
# List queues
docker exec instagram-rabbitmq rabbitmqctl list_queues name messages

# Should see only 3 queues:
# crawl_requests
# raw_recipe_data
# crawl_requests_failed
```

### Check Worker Logs
```bash
docker logs -f instagram-scraper-worker

# Look for:
# "Declared delayed exchange (x-delayed-message)"
# "Bound crawl_requests queue to delayed_exchange"
# "🔄 Scheduling retry X/3 in Xm (using delayed exchange)"
```

## Understanding Our Setup

### Queue Architecture

```
Application Components:
┌─────────────────────────────────────────────────┐
│                                                 │
│  ┌─────────────────┐      ┌─────────────────┐ │
│  │ crawl_requests  │      │ raw_recipe_data │ │
│  │                 │      │                 │ │
│  │ New URLs to     │      │ Successfully    │ │
│  │ scrape          │      │ scraped data    │ │
│  └─────────────────┘      └─────────────────┘ │
│                                                 │
│  ┌──────────────────────┐  ┌─────────────────┐│
│  │ delayed_exchange     │  │ crawl_requests_ ││
│  │                      │  │ failed          ││
│  │ Temporarily holds    │  │                 ││
│  │ messages for retry   │  │ After 3 failed  ││
│  └──────────────────────┘  │ retries         ││
│                             └─────────────────┘│
└─────────────────────────────────────────────────┘
```

### Message States

A message can be in one of these states:

1. **In crawl_requests** - Waiting to be processed
2. **Being processed** - Worker is scraping Instagram
3. **In delayed_exchange** - Waiting for retry delay to expire
4. **In raw_recipe_data** - Successfully scraped
5. **In crawl_requests_failed** - Failed after 3 retries

### Retry Flow

```
New Message
    ↓
┌─────────────────┐
│ crawl_requests  │ ← Message starts here
└─────────────────┘
    ↓
┌─────────┐
│  Try 1  │
└─────────┘
    ↓
  Error?
   Yes → Wait 5 min (delayed_exchange)  → Try 2 → Error?
                                                      Yes → Wait 15 min → Try 3 → Error?
                                                                                      Yes → failed queue
                                                                                      No  → raw_recipe_data
                                                      No  → raw_recipe_data
   No  → raw_recipe_data
```

## Configuration

### Change Retry Delays

Edit `src/worker.py:189-195`:

```python
if delay_type == 'long':
    # Adjust rate limit delays (in milliseconds)
    delay_ms = [300000, 900000, 3600000][min(retry_count, 2)]
else:
    # Adjust transient error delays (in milliseconds)
    delay_ms = [30000, 300000, 900000][min(retry_count, 2)]
```

### Change Max Retries

Edit `src/worker.py:182`:

```python
max_retries = 3  # Change to 5, 10, etc.
```

## Troubleshooting

### Understanding Error Messages

**"Plugin not found"**
```
Error: {:plugins_not_found, [:rabbitmq_delayed_message_exchange]}
```

**What this means:** RabbitMQ doesn't have the delayed message plugin installed.

**Why it happens:** The plugin isn't included by default in RabbitMQ.

**Solution:** Rebuild the RabbitMQ container with our custom Dockerfile that installs the plugin:
```bash
cd /path/to/recify
docker-compose down
docker-compose build rabbitmq
docker-compose up -d
```

---

**"Failed to declare delayed exchange"**
```
ERROR - Failed to declare delayed exchange. Is the plugin enabled?
```

**What this means:** The worker can't create the delayed exchange.

**Why it happens:**
1. Plugin not installed in RabbitMQ
2. Plugin installed but not enabled
3. Worker doesn't have permissions

**Solution:**
```bash
# Check if plugin is enabled
docker exec instagram-rabbitmq rabbitmq-plugins list

# Should show: [E*] rabbitmq_delayed_message_exchange
# E = Explicitly enabled
# * = Running

# If not enabled, enable it:
docker exec instagram-rabbitmq rabbitmq-plugins enable rabbitmq_delayed_message_exchange
docker-compose restart rabbitmq
```

---

**Messages not retrying**

**What this means:** Failed messages aren't being retried.

**Why it happens:**
1. Exchange not bound to queue
2. Message missing `x-delay` header
3. Worker not publishing to delayed_exchange

**Solution:** Check the binding:
```bash
docker exec instagram-rabbitmq rabbitmqctl list_bindings

# Should show:
# delayed_exchange  exchange  crawl_requests  queue  crawl_requests
```

If missing, restart the worker to recreate bindings:
```bash
docker-compose restart instagram-scraper
```

## Resources

- **Plugin Docs:** https://github.com/rabbitmq/rabbitmq-delayed-message-exchange
- **RabbitMQ Plugins:** https://www.rabbitmq.com/plugins.html
- **Message TTL:** https://www.rabbitmq.com/ttl.html

## FAQ

**Q: Why not just use `time.sleep()` in the worker?**

A: That would block the worker for minutes/hours, preventing it from processing other messages. With delayed exchange, the worker stays productive.

---

**Q: What happens if RabbitMQ restarts while messages are delayed?**

A: Messages are preserved! The exchange is durable, so delayed messages survive restarts and will still be delivered after the delay.

---

**Q: Can different messages have different delays?**

A: Yes! Each message has its own `x-delay` header. One message might delay 30 seconds while another delays 1 hour.

---

**Q: What if I want to change delay times?**

A: Just edit the delay calculations in `src/worker.py` - no need to recreate queues or restart RabbitMQ.

---

**Q: How do I see delayed messages in RabbitMQ UI?**

A: Open http://localhost:15672 (guest/guest), go to Exchanges → `delayed_exchange`. Messages waiting for delivery appear there.

---

**Q: What happens if a message fails 3 times?**

A: It's moved to `crawl_requests_failed` queue for manual review. You can inspect these messages and decide whether to republish them.

---

**Q: Does this work with other programming languages?**

A: Yes! Any AMQP client that supports RabbitMQ can use delayed exchanges. The `x-delay` header is language-agnostic.

## Summary

This implementation uses **RabbitMQ's Delayed Message Exchange Plugin** to handle retries elegantly:

✅ **Automatic timing** - RabbitMQ handles all delays
✅ **Non-blocking** - Worker stays productive during delays
✅ **Flexible** - Each message can have different delay
✅ **Reliable** - Messages persist across restarts
✅ **Simple** - Just set a header, RabbitMQ does the rest
✅ **Observable** - Monitor delays in RabbitMQ UI

**Key concept:** Instead of the worker waiting, we let RabbitMQ be the timer. The worker publishes a message with "deliver this in 5 minutes" and immediately moves on to other work.
