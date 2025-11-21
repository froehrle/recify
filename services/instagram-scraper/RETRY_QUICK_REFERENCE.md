# Retry Mechanism - Quick Reference

## 🎯 What's Implemented

**Delayed retry with exponential backoff** using RabbitMQ TTL queues.

## 📊 Retry Strategy

### Rate Limit Errors (401/403)
```
Attempt 1 → Wait 5 minutes   → Retry
Attempt 2 → Wait 15 minutes  → Retry
Attempt 3 → Wait 1 hour      → Retry
Attempt 4 → Move to failed queue
```

### Other Errors (network, etc.)
```
Attempt 1 → Wait 30 seconds  → Retry
Attempt 2 → Wait 5 minutes   → Retry
Attempt 3 → Wait 15 minutes  → Retry
Attempt 4 → Move to failed queue
```

## 🔧 Quick Commands

```bash
# Monitor queues in real-time
just watch-queues

# List all queues with details
just list-queues

# Check failed messages
just check-failed

# View worker logs
just logs-worker

# View RabbitMQ Management UI
just rabbitmq-ui
# Then open: http://localhost:15672 (guest/guest)
```

## 📦 Queue Structure

| Queue | Purpose | TTL |
|-------|---------|-----|
| `crawl_requests` | Main queue | - |
| `crawl_requests_retry_30s` | Quick retry | 30 sec |
| `crawl_requests_retry_300s` | Short delay | 5 min |
| `crawl_requests_retry_900s` | Medium delay | 15 min |
| `crawl_requests_retry_3600s` | Long delay | 1 hour |
| `crawl_requests_failed` | Permanent failures | - |
| `raw_recipe_data` | Successful results | - |

## 🎬 How Messages Flow

```
1. New Request → crawl_requests
2. Worker processes
3. On Error:
   ├─ Rate Limit? → Use long delays (5m, 15m, 1h)
   └─ Other Error? → Use short delays (30s, 5m, 15m)
4. Message → Delay Queue (sits and waits)
5. TTL expires → Auto-routes back to crawl_requests
6. Repeat up to 3 times
7. After max retries → crawl_requests_failed
```

## 📝 Log Messages

You'll see these in the logs:

```
✅ Successfully processed: https://...
⚠️  Instagram rate limit hit for https://...
🔄 Scheduling retry 1/3 in 5m (queue: crawl_requests_retry_300s)
❌ Max retries (3) reached. Moving to failed queue.
📦 Message moved to failed queue
```

## ⚙️ Configuration

Edit `src/worker.py`:

**Change retry delays:**
```python
# Line 51-56
delay_configs = [
    (30, "30s"),      # First retry
    (300, "5m"),      # Second retry
    (900, "15m"),     # Third retry
    (3600, "1h")      # Max retry
]
```

**Change max retries:**
```python
# Line 181
max_retries = 3  # Change to 5, 10, etc.
```

## 🐛 Troubleshooting

**Messages not retrying?**
```bash
# Check queue configuration
just list-queues | grep retry
```

**Too many failed messages?**
```bash
# Check what's failing
just check-failed
```

**Need to restart?**
```bash
just down
just build
just start
```

## 📚 Full Documentation

- **Implementation Details**: `docs/RETRY_IMPLEMENTATION_SUMMARY.md`
- **Strategy Options**: `docs/RETRY_MECHANISM.md`
