# Instagram Scraper Service

A microservice that extracts recipe data from Instagram posts using Celery and RabbitMQ.

## Features

- **Anonymous Access**: Works without Instagram credentials for public posts
- **Authenticated Access**: Better rate limits with Instagram session
- **Comment Extraction**: Finds author's most liked comment
- **Multiple Formats**: Supports posts, reels, and carousels
- **Docker Ready**: Complete containerized setup
- **Monitoring**: Celery Flower dashboard
- **Health Checks**: Built-in service health monitoring

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and start all services
just build-instagram-scraper
just start-instagram-service

# View logs
just logs-instagram-scraper

# With monitoring dashboard
just start-instagram-with-monitoring
```

### Option 2: Local Development

```bash
# Install dependencies
just install-instagram-scraper

# Start RabbitMQ
just start-rabbitmq

# Start worker
just start-instagram-worker
```

## Configuration

### Environment Variables

```bash
# Optional: Instagram Authentication (for better rate limits)
INSTAGRAM_USERNAME=your_username
INSTAGRAM_SESSION_FILE=instagram_sessions/session

# RabbitMQ (defaults work for local development)
RABBITMQ_URL=pyamqp://guest@localhost//
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
```

### Creating Instagram Session (Optional)

```bash
# Create authenticated session for higher rate limits
just create-instagram-session
```

## Usage

### Message Queue Integration

**Input Queue**: `crawl_requests`
```json
{
  "instagram_url": "https://www.instagram.com/p/ABC123/",
  "request_id": "req-001",
  "priority": 1
}
```

**Output Queue**: `raw_recipe_data`
```json
{
  "url": "https://www.instagram.com/p/ABC123/",
  "caption": "Delicious pasta recipe! 🍝",
  "media_urls": ["https://instagram.com/media1.jpg"],
  "author": "chef_username",
  "timestamp": "2024-01-15T10:30:00Z",
  "hashtags": ["pasta", "recipe"],
  "mentions": [],
  "likes_count": 150,
  "comments_count": 25,
  "author_top_comment": "Here's the full recipe!"
}
```

## Development

### Running Tests

```bash
# All tests
just test-instagram-scraper

# Unit tests only
just test-instagram-scraper-unit

# Integration tests only
just test-instagram-scraper-integration
```

### Code Quality

```bash
# Check code style
uv run ruff check .

# Format code
uv run black .
```

## Monitoring

### Dashboards

- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **Celery Flower**: http://localhost:5555 (when monitoring enabled)

### Health Checks

```bash
# Check service status
just health-instagram-service

# View logs
just logs-instagram-scraper
just logs-rabbitmq
```

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   UI/External   │───▶│   RabbitMQ   │───▶│ Instagram       │
│                 │    │              │    │ Scraper         │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                       │
                              ▼                       ▼
                       ┌──────────────┐    ┌─────────────────┐
                       │ raw_recipe   │◀───│ Recipe Schema   │
                       │ _data queue  │    │ Converter       │
                       └──────────────┘    └─────────────────┘
```

## Performance

### Rate Limits

- **Anonymous**: ~200 requests/hour
- **Authenticated**: ~1000+ requests/hour

### Scaling

```bash
# Scale workers horizontally
docker-compose up --scale instagram-scraper=3 -d
```

## Troubleshooting

### Common Issues

**Rate Limited**: Use authenticated session for higher limits
```bash
just create-instagram-session
```

**Container Issues**: Clean restart
```bash
just clean-instagram-service
just start-instagram-service
```

**Network Issues**: Check RabbitMQ connection
```bash
just logs-rabbitmq
```

## Security

- Uses non-root user in containers
- Session files mounted as volumes (not in images)
- Environment variables for credentials
- Anonymous access available (no credentials needed)