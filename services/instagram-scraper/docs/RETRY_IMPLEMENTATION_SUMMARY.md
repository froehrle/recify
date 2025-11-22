# Delayed Retry Mechanism - Implementation Summary

## ✅ What Was Implemented

A **delayed retry mechanism with RabbitMQ TTL** and exponential backoff for handling transient errors and Instagram rate limits.

## Architecture

```
┌─────────────────┐
│ crawl_requests  │ ◄─── Main queue (consumer listens here)
└─────────────────┘
         │
         │ On Error
         ▼
    ┌─────────┐
    │  Retry  │
    │ Logic   │
    └─────────┘
         │
         ├─ Rate Limit Error (401/403)
         │  ├─ Retry 1 → crawl_requests_retry_300s  (5 min)
         │  ├─ Retry 2 → crawl_requests_retry_900s  (15 min)
         │  └─ Retry 3 → crawl_requests_retry_3600s (1 hour)
         │
         ├─ Transient Error (network, etc)
         │  ├─ Retry 1 → crawl_requests_retry_30s   (30 sec)
         │  ├─ Retry 2 → crawl_requests_retry_300s  (5 min)
         │  └─ Retry 3 → crawl_requests_retry_900s  (15 min)
         │
         └─ After 3 retries → crawl_requests_failed
```

## Queue Configuration

### Main Queues
- **crawl_requests**: Primary queue for new requests
- **raw_recipe_data**: Successfully processed data
- **crawl_requests_failed**: Messages that failed after max retries

### Delay Queues (Auto-created on startup)
| Queue | TTL | Use Case |
|-------|-----|----------|
| `crawl_requests_retry_30s` | 30 seconds | Quick retry for network glitches |
| `crawl_requests_retry_300s` | 5 minutes | Rate limit cooldown / transient errors |
| `crawl_requests_retry_900s` | 15 minutes | Extended rate limit / repeated failures |
| `crawl_requests_retry_3600s` | 1 hour | Maximum backoff for rate limits |

Each delay queue is configured with:
- **x-message-ttl**: Time before message expires
- **x-dead-letter-exchange**: Default exchange (routes back to main queue)
- **x-dead-letter-routing-key**: `crawl_requests`

## How It Works

### 1. Message Processing
When a message fails, the worker:
1. Checks the retry count from message headers
2. Determines error type (rate limit vs other)
3. Calculates appropriate delay using exponential backoff
4. Publishes to delay queue with updated retry count

### 2. Automatic Retry
RabbitMQ handles the timing:
1. Message sits in delay queue for TTL duration
2. When TTL expires, RabbitMQ automatically routes message back to `crawl_requests`
3. Worker picks it up and retries
4. Process repeats up to 3 times

### 3. Exponential Backoff

**Rate Limit Errors (401/403):**
- Retry 1: 5 minutes
- Retry 2: 15 minutes
- Retry 3: 1 hour
- After retry 3: Move to failed queue

**Other Errors:**
- Retry 1: 30 seconds
- Retry 2: 5 minutes
- Retry 3: 15 minutes
- After retry 3: Move to failed queue

### 4. Message Headers

The worker tracks retry state using message headers:
```json
{
  "x-retry-count": 2,
  "x-first-attempt": 1732222800,
  "x-last-error": "Instagram rate limit: 401 Unauthorized..."
}
```

## Code Changes

### src/worker.py

#### 1. Queue Declaration (worker.py:36-74)
```python
# Declare delay queues with TTL for exponential backoff
delay_configs = [
    (30, "30s"),      # 30 seconds
    (300, "5m"),      # 5 minutes
    (900, "15m"),     # 15 minutes
    (3600, "1h")      # 1 hour
]

for delay_seconds, label in delay_configs:
    queue_name = f'crawl_requests_retry_{delay_seconds}s'
    self.channel.queue_declare(
        queue=queue_name,
        durable=True,
        arguments={
            'x-message-ttl': delay_seconds * 1000,
            'x-dead-letter-exchange': '',
            'x-dead-letter-routing-key': 'crawl_requests'
        }
    )
```

#### 2. Error Handling (worker.py:140-162)
```python
except InstagramRateLimitError as exc:
    # Rate limit error - use long delay
    retry_count = self._get_retry_count(properties)
    self._schedule_retry(body, properties, retry_count,
                        delay_type='long', error=str(exc))
    ch.basic_ack(delivery_tag=method.delivery_tag)

except Exception as exc:
    # Other errors - use short delay
    retry_count = self._get_retry_count(properties)
    self._schedule_retry(body, properties, retry_count,
                        delay_type='short', error=str(exc))
    ch.basic_ack(delivery_tag=method.delivery_tag)
```

#### 3. Retry Scheduling (worker.py:170-228)
```python
def _schedule_retry(self, body: bytes, properties,
                   retry_count: int, delay_type: str = 'short',
                   error: str = ''):
    """Schedule a delayed retry or move to failed queue"""
    max_retries = 3

    if retry_count >= max_retries:
        self._move_to_failed_queue(body, f"Max retries exceeded")
        return

    # Choose delay based on error type and retry count
    if delay_type == 'long':
        delay_seconds = [300, 900, 3600][min(retry_count, 2)]
    else:
        delay_seconds = [30, 300, 900][min(retry_count, 2)]

    retry_queue = f'crawl_requests_retry_{delay_seconds}s'

    # Publish to delay queue
    self.channel.basic_publish(...)
```

## Benefits

✅ **Worker never blocks** - No `time.sleep()` calls
✅ **Exponential backoff** - Respects Instagram rate limits
✅ **Automatic retry** - RabbitMQ handles timing
✅ **Observable** - All queues visible in RabbitMQ UI
✅ **Persistent** - Retries survive restarts
✅ **Flexible** - Different delays for different error types
✅ **Max retry limit** - Prevents infinite loops
✅ **Failed message tracking** - DLQ for manual review

## Monitoring

### Check Queue Status
```bash
# List all queues
docker exec instagram-rabbitmq rabbitmqctl list_queues name messages

# Check specific delay queue
docker exec instagram-rabbitmq rabbitmqctl list_queues | grep retry
```

### View Logs
```bash
# Watch worker logs
docker logs -f instagram-scraper-worker

# You'll see log messages like:
# 🔄 Scheduling retry 1/3 in 5m (queue: crawl_requests_retry_300s)
# ⚠️  Instagram rate limit hit for https://...
# ✅ Successfully processed: https://...
# ❌ Max retries (3) reached. Moving to failed queue.
```

### RabbitMQ Management UI
Access at http://localhost:15672 (guest/guest):
- View all queues including delay queues
- See message counts and rates
- Inspect message headers
- Move messages between queues manually

## Testing

### 1. Send Test Message
```bash
cd /path/to/instagram-scraper
python scripts/send_manual_request.py "https://www.instagram.com/p/test/"
```

### 2. Watch Retry Flow
```bash
# Terminal 1: Watch logs
docker logs -f instagram-scraper-worker

# Terminal 2: Monitor queues
watch -n 2 'docker exec instagram-rabbitmq rabbitmqctl list_queues name messages'
```

### 3. Expected Flow for Rate Limit
```
1. Message sent to crawl_requests
2. Worker processes → Rate limit error
3. Message moved to crawl_requests_retry_300s (5 min)
4. After 5 min → Auto-routes back to crawl_requests
5. Worker retries → Still rate limited
6. Message moved to crawl_requests_retry_900s (15 min)
7. After 15 min → Auto-routes back to crawl_requests
8. Worker retries → Still rate limited
9. Message moved to crawl_requests_retry_3600s (1 hour)
10. After 1 hour → Auto-routes back to crawl_requests
11. Worker retries → Still rate limited
12. Message moved to crawl_requests_failed (permanent)
```

## Configuration

### Adjust Retry Delays
Edit `src/worker.py:51-56`:
```python
delay_configs = [
    (30, "30s"),      # Change first retry delay
    (300, "5m"),      # Change second retry delay
    (900, "15m"),     # Change third retry delay
    (3600, "1h")      # Change max retry delay
]
```

### Adjust Max Retries
Edit `src/worker.py:181`:
```python
max_retries = 3  # Change to 5, 10, etc.
```

### Adjust Backoff Strategy
Edit `src/worker.py:188-194`:
```python
if delay_type == 'long':
    # Example: More aggressive backoff
    delay_seconds = [600, 1800, 7200][min(retry_count, 2)]
```

## Troubleshooting

### Messages Stuck in Delay Queue
**Cause**: TTL not configured correctly
**Fix**: Delete queue and restart worker to recreate

```bash
docker exec instagram-rabbitmq rabbitmqctl delete_queue crawl_requests_retry_300s
docker-compose restart instagram-scraper
```

### Messages Not Retrying
**Check**: Dead-letter routing configuration
```bash
docker exec instagram-rabbitmq rabbitmqctl list_queues name arguments
```

Should show `x-dead-letter-routing-key: crawl_requests`

### Too Many Failed Messages
**Cause**: Max retries too low or delays too short
**Action**:
1. Check error types in `crawl_requests_failed` queue
2. Adjust retry delays or max retries
3. Manually republish from failed queue if needed

## Next Steps

Potential enhancements:
- [ ] Add Prometheus metrics for retry counts
- [ ] Implement priority-based retries
- [ ] Add retry budget (max retries per time window)
- [ ] Create admin tool to republish failed messages
- [ ] Add alerts for high failed message count
- [ ] Implement circuit breaker pattern
