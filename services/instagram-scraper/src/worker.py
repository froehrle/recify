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

        # Declare queues (durable for persistence)
        self.channel.queue_declare(queue='crawl_requests', durable=True)
        self.channel.queue_declare(queue='raw_recipe_data', durable=True)

        # Declare dead letter queue for failed messages
        self.channel.queue_declare(queue='crawl_requests_failed', durable=True)

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
            # Rate limit error - don't requeue, move to failed queue
            logger.warning(f"⚠️  Instagram rate limit hit for {instagram_url}. Message moved to failed queue.")
            logger.warning(f"   Cooling down for {self.rate_limit_cooldown}s before processing next message...")

            # Move to failed queue for manual review
            self._move_to_failed_queue(body, str(exc))
            ch.basic_ack(delivery_tag=method.delivery_tag)

            # Wait before processing next message to respect rate limits
            time.sleep(self.rate_limit_cooldown)

        except ValueError as exc:
            # Validation errors - don't requeue
            logger.error(f"❌ Invalid message format for {instagram_url}: {exc}")
            self._move_to_failed_queue(body, str(exc))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as exc:
            # Other errors - check retry count and potentially requeue
            retry_count = self._get_retry_count(properties)
            max_retries = 3

            if retry_count >= max_retries:
                logger.error(f"❌ Failed after {retry_count} retries for {instagram_url}: {exc}")
                self._move_to_failed_queue(body, str(exc))
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logger.warning(f"⚠️  Error processing {instagram_url} (retry {retry_count + 1}/{max_retries}): {exc}")
                # Requeue with incremented retry count
                new_headers = properties.headers or {}
                new_headers['x-retry-count'] = retry_count + 1
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _get_retry_count(self, properties) -> int:
        """Get retry count from message headers"""
        if properties and properties.headers and 'x-retry-count' in properties.headers:
            return properties.headers['x-retry-count']
        return 0

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
