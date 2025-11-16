#!/usr/bin/env python3
"""
Consume and display results from the raw_recipe_data queue.
This shows the extracted Instagram data.
"""

import json
import pika
import sys
from datetime import datetime


def callback(ch, method, properties, body):
    """Process received message."""
    try:
        data = json.loads(body)

        print("\n" + "="*70)
        print("📥 NEW RECIPE DATA RECEIVED")
        print("="*70)

        print(f"\n📍 URL: {data.get('url', 'N/A')}")
        print(f"👤 Author: {data.get('author', 'N/A')}")
        print(f"📅 Timestamp: {data.get('timestamp', 'N/A')}")

        caption = data.get('caption', '')
        if caption:
            print(f"\n📝 Caption ({len(caption)} chars):")
            print(f"   {caption[:200]}{'...' if len(caption) > 200 else ''}")

        media_urls = data.get('media_urls', [])
        print(f"\n🖼️  Media ({len(media_urls)} items):")
        for i, url in enumerate(media_urls, 1):
            print(f"   {i}. {url}")

        hashtags = data.get('hashtags', [])
        if hashtags:
            print(f"\n🏷️  Hashtags: {', '.join(f'#{tag}' for tag in hashtags)}")

        mentions = data.get('mentions', [])
        if mentions:
            print(f"👥 Mentions: {', '.join(f'@{user}' for user in mentions)}")

        likes = data.get('likes_count')
        comments = data.get('comments_count')
        if likes or comments:
            print(f"\n📊 Engagement:")
            if likes:
                print(f"   ❤️  Likes: {likes:,}")
            if comments:
                print(f"   💬 Comments: {comments:,}")

        top_comment = data.get('author_top_comment')
        if top_comment:
            print(f"\n💭 Author's top comment:")
            print(f"   {top_comment}")

        print("\n" + "="*70 + "\n")

        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError as e:
        print(f"❌ Error decoding JSON: {e}")
        print(f"   Raw body: {body}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    """Start consuming messages from raw_recipe_data queue."""

    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║         Raw Recipe Data Consumer - Listening...          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)

    print("🔌 Connecting to RabbitMQ...")

    try:
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost')
        )
        channel = connection.channel()

        # Declare queue (ensures it exists)
        queue_name = 'raw_recipe_data'
        channel.queue_declare(queue=queue_name, durable=True)

        print(f"✅ Connected to queue: {queue_name}")
        print(f"⏳ Waiting for messages... (Press Ctrl+C to exit)\n")

        # Set up consumer
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback
        )

        # Start consuming
        channel.start_consuming()

    except KeyboardInterrupt:
        print("\n\n👋 Stopping consumer...")
        sys.exit(0)
    except pika.exceptions.AMQPConnectionError:
        print("❌ Could not connect to RabbitMQ. Is it running?")
        print("   Start with: just instagram-scraper::start")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()