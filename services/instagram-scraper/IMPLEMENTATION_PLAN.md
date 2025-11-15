# Instagram Scraper Service - Implementation Plan

## Overview
Celery-only microservice that consumes crawl requests from RabbitMQ and publishes raw recipe data using instaloader.

## Architecture

### Message Flow
```
UI/External → RabbitMQ(crawl_requests) → Instagram Scraper → RabbitMQ(raw_recipe_data) → Recipe Schema Converter
```

### Queue Design
- **Consume from**: `crawl_requests` queue
- **Publish to**: `raw_recipe_data` queue

## Project Structure

```
services/instagram-scraper/
├── pyproject.toml            # Python dependencies and project config
├── .python-version           # Python version for uv
├── celeryapp.py              # Celery application configuration
├── tasks.py                  # Celery task definitions
├── instagram_crawler.py      # Core Instagram extraction logic
├── models.py                 # Data models for requests/responses
├── config.py                 # Configuration settings
├── docker-compose.yml        # Local development setup
├── Dockerfile                # Service containerization
├── tests/
│   ├── test_crawler.py       # Unit tests for crawler logic
│   └── test_integration.py   # Integration tests
└── README.md                 # Service documentation
```

## Implementation Details

### 1. Dependencies (`pyproject.toml`)
```toml
[project]
name = "instagram-scraper"
version = "0.1.0"
description = "Instagram scraper service for recipe data extraction"
dependencies = [
    "celery[redis]>=5.3.4",
    "instaloader>=4.10.3",
    "pydantic>=2.5.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-celery>=0.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.black]
line-length = 88
target-version = ["py311"]
```

### 2. Celery Configuration (`celeryapp.py`)
```python
from celery import Celery
from config import RABBITMQ_URL

app = Celery('instagram-scraper')
app.conf.update(
    broker_url=RABBITMQ_URL,
    result_backend=None,  # No result storage needed
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.crawl_instagram_post': {'queue': 'crawl_requests'},
    }
)
```

### 3. Task Definitions (`tasks.py`)
```python
from celery import Celery
from celeryapp import app
from instagram_crawler import InstagramCrawler
from models import CrawlRequest, RawRecipeData
import json

@app.task(bind=True, name='crawl_instagram_post')
def crawl_instagram_post(self, request_data: dict):
    """
    Consume: crawl_requests queue
    Process: Extract Instagram post data
    Publish: raw_recipe_data queue
    """
    try:
        request = CrawlRequest(**request_data)
        crawler = InstagramCrawler()

        # Extract post data using instaloader
        raw_data = crawler.extract_post_data(request.instagram_url)

        # Publish to raw_recipe_data queue
        publish_raw_recipe_data.delay(raw_data.dict())

        return {"status": "success", "url": request.instagram_url}

    except Exception as exc:
        self.retry(countdown=60, max_retries=3, exc=exc)

@app.task(name='publish_raw_recipe_data')
def publish_raw_recipe_data(raw_data: dict):
    """
    Publish extracted data to raw_recipe_data queue
    """
    # Celery automatically handles publishing to the queue
    pass
```

### 4. Instagram Crawler (`instagram_crawler.py`)
```python
import instaloader
from models import RawRecipeData
from typing import Optional
from datetime import datetime

class InstagramCrawler:
    def __init__(self):
        self.loader = instaloader.Instaloader()
        # Configure instaloader for minimal footprint
        self.loader.download_pictures = False
        self.loader.download_videos = False
        self.loader.download_video_thumbnails = False

    def extract_post_data(self, instagram_url: str) -> RawRecipeData:
        """
        Extract post data from Instagram URL
        """
        try:
            # Extract shortcode from URL
            shortcode = self._extract_shortcode(instagram_url)

            # Get post using instaloader
            post = instaloader.Post.from_shortcode(
                self.loader.context,
                shortcode
            )

            # Extract relevant data
            raw_data = RawRecipeData(
                url=instagram_url,
                caption=post.caption or "",
                media_urls=self._extract_media_urls(post),
                author=post.owner_username,
                timestamp=post.date_utc,
                hashtags=list(post.caption_hashtags),
                mentions=list(post.caption_mentions),
                likes_count=post.likes,
                comments_count=post.comments,
                author_top_comment=self._extract_author_top_comment(post)
            )

            return raw_data

        except Exception as e:
            raise Exception(f"Failed to extract Instagram post: {str(e)}")

    def _extract_shortcode(self, url: str) -> str:
        """Extract shortcode from Instagram URL"""
        # Handle various Instagram URL formats
        if '/p/' in url:
            return url.split('/p/')[-1].split('/')[0]
        elif '/reel/' in url:
            return url.split('/reel/')[-1].split('/')[0]
        else:
            raise ValueError(f"Invalid Instagram URL format: {url}")

    def _extract_media_urls(self, post) -> list[str]:
        """Extract media URLs from post"""
        media_urls = []
        if post.url:
            media_urls.append(post.url)
        # Handle carousel posts
        for node in post.get_sidecar_nodes():
            if node.display_url:
                media_urls.append(node.display_url)
        return media_urls
 
    def _extract_author_top_comment(self, post) -> Optional[str]:
        """Extract the author's most liked comment"""
        try:
            # Get comments from the post
            comments = post.get_comments()
            author_username = post.owner_username

            # Find all comments by the author
            author_comments = []
            for comment in comments:
                if comment.owner.username == author_username:
                    author_comments.append(comment)

            if not author_comments:
                return None

            # Find the comment with the most likes
            most_liked_comment = max(author_comments, key=lambda c: c.likes)
            return most_liked_comment.text

        except Exception:
            # If comments can't be fetched, return None
            return None
```

### 5. Data Models (`models.py`)
```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import List, Optional

class CrawlRequest(BaseModel):
    instagram_url: HttpUrl
    request_id: Optional[str] = None
    priority: int = 1

class RawRecipeData(BaseModel):
    url: str
    caption: str
    media_urls: List[str]
    author: str
    timestamp: datetime
    hashtags: List[str]
    mentions: List[str]
    likes_count: Optional[int] = None
    comments_count: Optional[int] = None
    author_top_comment: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### 6. Configuration (`config.py`)
```python
import os
from dotenv import load_dotenv

load_dotenv()

# RabbitMQ Configuration
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'pyamqp://guest@localhost//')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'guest')

# Celery Configuration
CELERY_BROKER_URL = RABBITMQ_URL
CELERY_RESULT_BACKEND = None

# Instagram Configuration
INSTAGRAM_SESSION_FILE = os.getenv('INSTAGRAM_SESSION_FILE', 'session')
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
```

## Development Setup

### 1. Local Development (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  rabbitmq:
    image: rabbitmq:3.11-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  instagram-scraper:
    build: .
    depends_on:
      - rabbitmq
    environment:
      RABBITMQ_URL: pyamqp://guest@rabbitmq//
    volumes:
      - .:/app
    command: celery -A celeryapp worker --loglevel=info

volumes:
  rabbitmq_data:
```

### 2. Container Setup (`Dockerfile`)
```dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .python-version ./

# Install dependencies
RUN uv sync --frozen

COPY . .

CMD ["uv", "run", "celery", "-A", "celeryapp", "worker", "--loglevel=info"]
```

## Testing Strategy

### Integration Test (`tests/test_integration.py`)
```python
import pytest
from celery import Celery
from tasks import crawl_instagram_post
from models import CrawlRequest

@pytest.fixture
def celery_app():
    app = Celery('test-instagram-scraper')
    app.conf.update(
        broker_url='memory://',
        result_backend='cache+memory://',
        task_always_eager=True,
    )
    return app

def test_instagram_post_extraction():
    """
    Integration test: Input Instagram URL, expect caption extraction
    """
    # Test with a known Instagram post URL
    test_url = "https://www.instagram.com/p/SAMPLE_SHORTCODE/"

    request_data = {
        "instagram_url": test_url,
        "request_id": "test-001"
    }

    # Execute task
    result = crawl_instagram_post.delay(request_data)

    # Assertions
    assert result.status == 'SUCCESS'
    assert result.result['status'] == 'success'
    assert result.result['url'] == test_url

    # Verify caption was extracted (mock or use actual test post)
    # This would need a test Instagram post with known caption
```

## Deployment Commands

### Local Development with UV
```bash
# Start RabbitMQ
docker-compose up rabbitmq -d

# Install dependencies with uv
uv sync

# Start Celery worker
uv run celery -A celeryapp worker --loglevel=info

# Run tests
uv run pytest

# Monitor with Flower (optional)
uv run celery -A celeryapp flower
```

### Production Deployment
```bash
# Build and start all services
docker-compose up --build -d

# Scale workers
docker-compose up --scale instagram-scraper=3 -d
```

## Queue Message Formats

### Input Message (crawl_requests)
```json
{
  "instagram_url": "https://www.instagram.com/p/ABC123/",
  "request_id": "req-001",
  "priority": 1
}
```

### Output Message (raw_recipe_data)
```json
{
  "url": "https://www.instagram.com/p/ABC123/",
  "caption": "Delicious pasta recipe! 🍝 #pasta #recipe",
  "media_urls": ["https://instagram.com/media1.jpg"],
  "author": "chef_username",
  "timestamp": "2024-01-15T10:30:00Z",
  "hashtags": ["pasta", "recipe"],
  "mentions": [],
  "likes_count": 150,
  "comments_count": 25,
  "author_top_comment": "Here's the full recipe in the comments! Let me know if you try it 👨‍🍳"
}
```

## Error Handling & Retry Strategy

- **Network errors**: Retry 3 times with exponential backoff
- **Rate limiting**: Implement delays and respect Instagram's rate limits
- **Invalid URLs**: Log error and mark task as failed
- **Private posts**: Handle gracefully with appropriate error message

## Monitoring & Logging

- **Celery Flower**: Web-based monitoring dashboard
- **Structured logging**: JSON format for easy parsing
- **Metrics tracking**: Task success/failure rates, processing time
- **Health checks**: Endpoint to verify service status