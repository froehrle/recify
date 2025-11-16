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
from instagram_crawler import InstagramCrawler
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

            logger.info(f"Processing crawl request: {request_data.get('instagram_url', 'unknown')}")

            # Validate request data
            request = CrawlRequest(**request_data)

            # Extract post data
            raw_data = self.crawler.extract_post_data(str(request.instagram_url))

            # Publish to next queue
            self.publish_raw_recipe_data(raw_data)

            # Acknowledge message after successful processing
            ch.basic_ack(delivery_tag=method.delivery_tag)

            logger.info(f"Successfully processed: {request.instagram_url}")

        except Exception as exc:
            logger.error(f"Failed to process message: {exc}", exc_info=True)

            # Reject and requeue for retry (could implement max retry logic here)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

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
