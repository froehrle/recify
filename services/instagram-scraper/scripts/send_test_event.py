#!/usr/bin/env python3
"""
Send a test crawl request to the Instagram Scraper queue using pika.

Usage:
    python send_test_event.py [INSTAGRAM_URL]

Example:
    python send_test_event.py https://www.instagram.com/p/ABC123/
"""

import sys
import json
import pika
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import RABBITMQ_HOST


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
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()

        # Declare queue (durable for persistence)
        channel.queue_declare(queue='crawl_requests', durable=True)

        # Publish message
        channel.basic_publish(
            exchange='',
            routing_key='crawl_requests',
            body=json.dumps(test_request),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json'
            )
        )

        connection.close()

        print(f"\n✅ Request sent successfully!")
        print(f"   Queue: crawl_requests")
        print(f"\n💡 Monitor progress:")
        print(f"   tail -f worker.log")
        print(f"   http://localhost:15672 (RabbitMQ Management)")
        print(f"\n💡 Consume results:")
        print(f"   python scripts/consume_results.py\n")

        return 0

    except Exception as e:
        print(f"\n❌ Failed to send request: {e}")
        print(f"\n💡 Make sure RabbitMQ is running:")
        print(f"   docker-compose up -d rabbitmq\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
