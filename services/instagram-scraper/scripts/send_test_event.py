#!/usr/bin/env python3
"""
Send a test crawl request to the Instagram Scraper queue.

Usage:
    python send_test_event.py [INSTAGRAM_URL]

Example:
    python send_test_event.py https://www.instagram.com/p/ABC123/
"""

import sys
from datetime import datetime
from tasks import crawl_instagram_post


def main():
    """Send a test crawl request."""

    # Get URL from command line or use default
    if len(sys.argv) > 1:
        instagram_url = sys.argv[1]
    else:
        # Default test URL - a real public Instagram post
        instagram_url = "https://www.instagram.com/p/DITcnygqFll/"
        print(f"⚠️  No URL provided, using default: {instagram_url}")
        print(f"   Usage: python send_test_event.py <INSTAGRAM_URL>\n")

    # Create test request
    request_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    test_request = {
        'instagram_url': instagram_url,
        'request_id': request_id,
        'priority': 1
    }

    print("="*60)
    print("📤 Sending Crawl Request")
    print("="*60)
    print(f"URL:         {test_request['instagram_url']}")
    print(f"Request ID:  {test_request['request_id']}")
    print(f"Priority:    {test_request['priority']}")
    print("="*60)

    try:
        # Send the task to the queue
        result = crawl_instagram_post.delay(test_request)

        print(f"\n✅ Task sent successfully!")
        print(f"   Task ID: {result.id}")
        print(f"   Queue: crawl_requests")
        print(f"\n💡 Monitor progress:")
        print(f"   docker-compose logs -f instagram-scraper")
        print(f"   http://localhost:15672 (RabbitMQ Management)\n")

        return 0

    except Exception as e:
        print(f"\n❌ Failed to send task: {e}")
        print(f"\n💡 Make sure services are running:")
        print(f"   docker-compose up -d\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
