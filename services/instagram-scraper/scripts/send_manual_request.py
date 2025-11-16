#!/usr/bin/env python3
"""
Send a message directly to RabbitMQ using Pika (bypasses Celery).
This is useful for testing the queue directly.
"""

import json
import pika
import sys
from datetime import datetime


def send_message_to_queue(instagram_url, queue_name='crawl_requests'):
    """Send a message directly to RabbitMQ queue."""

    # Create message
    message = {
        'instagram_url': instagram_url,
        'request_id': f'manual-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
        'priority': 1
    }

    # Connect to RabbitMQ
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost')
    )
    channel = connection.channel()

    # Declare queue (ensures it exists)
    channel.queue_declare(queue=queue_name, durable=True)

    # Send message
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
            content_type='application/json'
        )
    )

    print(f"✅ Message sent to queue '{queue_name}'")
    print(f"   URL: {message['instagram_url']}")
    print(f"   Request ID: {message['request_id']}")

    connection.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://www.instagram.com/p/DITcnygqFll/"
        print(f"Using default URL: {url}\n")

    send_message_to_queue(url)
