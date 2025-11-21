#!/usr/bin/env python3
"""
Start Instagram Scraper services and send a test crawl request.

This script:
1. Starts RabbitMQ and Instagram scraper worker via Docker Compose
2. Waits for services to be ready
3. Sends a test crawl request to the queue
4. Shows how to monitor the results
"""

import subprocess
import time
import sys
import json
import pika


def run_command(cmd, description):
    """Run a shell command and print the result."""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Success")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ Failed")
        if result.stderr:
            print(result.stderr)
        return False
    return True


def wait_for_rabbitmq(timeout=30):
    """Wait for RabbitMQ to be ready."""
    print(f"\n⏳ Waiting for RabbitMQ to be ready (max {timeout}s)...")

    for i in range(timeout):
        result = subprocess.run(
            "docker-compose exec -T rabbitmq rabbitmqctl status",
            shell=True,
            capture_output=True,
            text=True,
            cwd="/Users/benny/hdm-local/recify/services/instagram-scraper"
        )
        if result.returncode == 0:
            print("✅ RabbitMQ is ready!")
            return True

        print(f"   Waiting... ({i+1}/{timeout})", end='\r')
        time.sleep(1)

    print("\n❌ RabbitMQ failed to start in time")
    return False


def main():
    """Main execution flow."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     Instagram Scraper Service - Start & Test Script      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # Step 1: Stop any existing containers
    run_command(
        "docker-compose down",
        "Stopping existing containers"
    )

    # Step 2: Start services
    if not run_command(
        "docker-compose up -d",
        "Starting RabbitMQ and Instagram Scraper services"
    ):
        sys.exit(1)

    # Step 3: Wait for RabbitMQ to be ready
    if not wait_for_rabbitmq():
        sys.exit(1)

    # Give the worker a moment to start
    print("\n⏳ Waiting for worker to initialize (5s)...")
    time.sleep(5)

    # Step 4: Send a test crawl request
    print(f"\n{'='*60}")
    print("📤 Sending test crawl request")
    print(f"{'='*60}")

    # Example Instagram post URL (using a public post)
    test_url = "https://www.instagram.com/p/DITcnygqFll/"  # Replace with actual URL

    test_request = {
        'instagram_url': test_url,
        'request_id': 'test-request-001',
        'priority': 1
    }

    print(f"\n📝 Request details:")
    print(f"   URL: {test_request['instagram_url']}")
    print(f"   Request ID: {test_request['request_id']}")
    print(f"   Priority: {test_request['priority']}")

    try:
        # Send message directly to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost')
        )
        channel = connection.channel()
        channel.queue_declare(queue='crawl_requests', durable=True)

        channel.basic_publish(
            exchange='',
            routing_key='crawl_requests',
            body=json.dumps(test_request),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )

        connection.close()

        print(f"\n✅ Task sent successfully!")
        print(f"   Queue: crawl_requests")
    except Exception as e:
        print(f"\n❌ Failed to send task: {e}")
        sys.exit(1)

    # Step 5: Show monitoring options
    print(f"\n{'='*60}")
    print("📊 Monitoring Options")
    print(f"{'='*60}")
    print("""
1. View worker logs:
   docker-compose logs -f instagram-scraper

2. View RabbitMQ logs:
   docker-compose logs -f rabbitmq

3. RabbitMQ Management UI:
   http://localhost:15672
   Username: guest
   Password: guest

4. Check queue status:
   docker-compose exec rabbitmq rabbitmqctl list_queues

5. Stop services:
   docker-compose down
    """)

    print(f"\n{'='*60}")
    print("🎉 Setup complete! Check the logs above for task execution.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
