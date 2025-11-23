"""
RabbitMQ worker for consuming crawl requests using pika.

This worker:
- Consumes from 'crawl_requests' queue
- Processes Instagram URLs using InstagramCrawler
- Publishes results to 'raw_recipe_data' queue
"""
import pika
import json
import logging
import signal
import sys
import time
from instagram_crawler import InstagramCrawler, InstagramRateLimitError
from models import CrawlRequest, RawRecipeData
from config import RABBITMQ_HOST

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CrawlWorker:
    """Worker that processes Instagram crawl requests from RabbitMQ"""

    def __init__(self):
        self.connection = None
        self.channel = None
        self.crawler = InstagramCrawler()
        self.should_stop = False
        self.rate_limit_cooldown = 60  # seconds to wait after rate limit

    def connect(self):
        """Establish connection to RabbitMQ"""
        logger.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}")
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        self.channel = self.connection.channel()

        # Declare main queues (durable for persistence)
        self.channel.queue_declare(queue='crawl_requests', durable=True)
        self.channel.queue_declare(queue='raw_recipe_data', durable=True)
        self.channel.queue_declare(queue='crawl_requests_failed', durable=True)

        # Declare delayed message exchange (requires rabbitmq_delayed_message_exchange plugin)
        # This replaces the 4 delay queues with a single exchange
        try:
            self.channel.exchange_declare(
                exchange='delayed_exchange',
                exchange_type='x-delayed-message',
                arguments={'x-delayed-type': 'direct'},
                durable=True
            )
            logger.info("Declared delayed exchange (x-delayed-message)")

            # Bind main queue to delayed exchange
            self.channel.queue_bind(
                queue='crawl_requests',
                exchange='delayed_exchange',
                routing_key='crawl_requests'
            )
            logger.info("Bound crawl_requests queue to delayed_exchange")

        except Exception as e:
            logger.error(f"Failed to declare delayed exchange. Is the plugin enabled? Error: {e}")
            raise

        # Process one message at a time (QoS)
        self.channel.basic_qos(prefetch_count=1)

        logger.info("Connected to RabbitMQ successfully")

    def publish_raw_recipe_data(self, raw_data: RawRecipeData):
        """Publish extracted data to raw_recipe_data queue"""
        try:
            logger.info(f"Publishing raw recipe data for post: {raw_data.url}")

            # Prepare message
            message = raw_data.model_dump()
            message['timestamp'] = raw_data.timestamp.isoformat()

            # Publish with persistence
            self.channel.basic_publish(
                exchange='',
                routing_key='raw_recipe_data',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )

            logger.info(f"Successfully published recipe data: {raw_data.url}")

        except Exception as exc:
            logger.error(f"Failed to publish raw recipe data: {exc}")
            raise

    def process_message(self, ch, method, properties, body):
        """Process a single crawl request message"""
        instagram_url = "unknown"
        try:
            # Parse message
            raw_data = json.loads(body.decode())
            logger.debug(f"Received message: {raw_data} (type: {type(raw_data)})")

            # Handle both dict and list (in case of old message format)
            if isinstance(raw_data, list):
                # If it's a list, take the first element
                if len(raw_data) > 0 and isinstance(raw_data[0], dict):
                    request_data = raw_data[0]
                    logger.warning("Received message as list, using first element")
                else:
                    raise ValueError(f"Invalid message format: expected dict or list of dicts, got {type(raw_data)}")
            elif isinstance(raw_data, dict):
                request_data = raw_data
            else:
                raise ValueError(f"Invalid message format: expected dict or list, got {type(raw_data)}")

            instagram_url = request_data.get('instagram_url', 'unknown')
            logger.info(f"Processing crawl request: {instagram_url}")

            # Validate request data
            request = CrawlRequest(**request_data)

            # Extract post data
            raw_data = self.crawler.extract_post_data(str(request.instagram_url))

            # Publish to next queue
            self.publish_raw_recipe_data(raw_data)

            # Acknowledge message after successful processing
            ch.basic_ack(delivery_tag=method.delivery_tag)

            logger.info(f"✅ Successfully processed: {request.instagram_url}")

        except InstagramRateLimitError as exc:
            # Rate limit error - use long delay with exponential backoff
            retry_count = self._get_retry_count(properties)
            logger.warning(f"⚠️  Instagram rate limit hit for {instagram_url}")

            # Schedule retry with long delay
            self._schedule_retry(body, properties, retry_count, delay_type='long', error=str(exc))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except ValueError as exc:
            # Validation errors - don't retry, these won't succeed
            logger.error(f"❌ Invalid message format for {instagram_url}: {exc}")
            self._move_to_failed_queue(body, str(exc))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as exc:
            # Other errors - use short delay for transient issues
            retry_count = self._get_retry_count(properties)
            logger.warning(f"⚠️  Error processing {instagram_url}: {exc}")

            # Schedule retry with short delay
            self._schedule_retry(body, properties, retry_count, delay_type='short', error=str(exc))
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _get_retry_count(self, properties) -> int:
        """Get retry count from message headers"""
        if properties and properties.headers and 'x-retry-count' in properties.headers:
            return properties.headers['x-retry-count']
        return 0

    def _schedule_retry(self, body: bytes, properties, retry_count: int, delay_type: str = 'short', error: str = ''):
        """
        Schedule a delayed retry using RabbitMQ delayed message exchange.

        Args:
            body: Original message body
            properties: Message properties
            retry_count: Current retry count
            delay_type: 'short' for transient errors, 'long' for rate limits
            error: Error message for logging
        """
        max_retries = 3

        if retry_count >= max_retries:
            logger.error(f"❌ Max retries ({max_retries}) reached. Moving to failed queue.")
            self._move_to_failed_queue(body, f"Max retries exceeded. Last error: {error}")
            return

        # Choose delay based on error type and retry count (in milliseconds)
        if delay_type == 'long':
            # Exponential backoff for rate limits: 5min → 15min → 1hour
            delay_ms = [300000, 900000, 3600000][min(retry_count, 2)]
        else:
            # Short delays for transient errors: 30s → 5min → 15min
            delay_ms = [30000, 300000, 900000][min(retry_count, 2)]

        # Update message headers
        new_headers = properties.headers or {}
        new_headers['x-retry-count'] = retry_count + 1
        new_headers['x-first-attempt'] = new_headers.get('x-first-attempt', int(time.time()))
        new_headers['x-last-error'] = error[:500]  # Truncate long errors
        new_headers['x-delay'] = delay_ms  # Delayed message exchange uses this header

        # Calculate time labels for logging
        delay_seconds = delay_ms // 1000
        if delay_seconds < 60:
            delay_label = f"{delay_seconds}s"
        elif delay_seconds < 3600:
            delay_label = f"{delay_seconds // 60}m"
        else:
            delay_label = f"{delay_seconds // 3600}h"

        logger.info(f"🔄 Scheduling retry {retry_count + 1}/{max_retries} in {delay_label} (using delayed exchange)")

        try:
            # Publish to delayed exchange with x-delay header
            # The exchange will hold the message and deliver it to crawl_requests after delay
            self.channel.basic_publish(
                exchange='delayed_exchange',
                routing_key='crawl_requests',
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                    headers=new_headers
                )
            )
        except Exception as e:
            logger.error(f"Failed to schedule retry: {e}")
            self._move_to_failed_queue(body, f"Retry scheduling failed: {e}")

    def _move_to_failed_queue(self, original_body: bytes, error_msg: str):
        """Move failed message to dead letter queue"""
        try:
            failed_message = {
                'original_message': json.loads(original_body.decode()),
                'error': error_msg,
                'timestamp': time.time()
            }

            self.channel.basic_publish(
                exchange='',
                routing_key='crawl_requests_failed',
                body=json.dumps(failed_message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            logger.info(f"📦 Message moved to failed queue")
        except Exception as e:
            logger.error(f"Failed to move message to failed queue: {e}")

    def start(self):
        """Start consuming messages"""
        logger.info("Starting worker...")

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        # Connect to RabbitMQ
        self.connect()

        # Start consuming
        logger.info("Waiting for messages from 'crawl_requests' queue. Press CTRL+C to exit.")
        self.channel.basic_consume(
            queue='crawl_requests',
            on_message_callback=self.process_message,
            auto_ack=False  # Manual acknowledgment for reliability
        )

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.stop()

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    def stop(self):
        """Stop consuming and close connections"""
        if self.channel and self.channel.is_open:
            logger.info("Stopping consumer...")
            self.channel.stop_consuming()

        if self.connection and self.connection.is_open:
            logger.info("Closing connection...")
            self.connection.close()

        logger.info("Worker stopped")
        sys.exit(0)


def main():
    """Entry point for the worker"""
    worker = CrawlWorker()
    worker.start()


if __name__ == '__main__':
    main()
