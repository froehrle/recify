from celeryapp import app
from instagram_crawler import InstagramCrawler
from models import CrawlRequest, RawRecipeData
import json
import logging
import pika
from config import RABBITMQ_HOST

logger = logging.getLogger(__name__)

@app.task(bind=True, name='crawl_instagram_post', max_retries=3)
def crawl_instagram_post(self, request_data: dict):
    """
    Consume: crawl_requests queue
    Process: Extract Instagram post data
    Publish: raw_recipe_data queue
    """
    try:
        logger.info(f"Processing crawl request: {request_data}")

        # Validate request data
        request = CrawlRequest(**request_data)

        # Create crawler instance
        crawler = InstagramCrawler()

        # Extract post data using instaloader
        raw_data = crawler.extract_post_data(str(request.instagram_url))

        # Publish to raw_recipe_data queue (plain JSON for TypeScript consumer)
        publish_raw_recipe_data(raw_data.model_dump())

        logger.info(f"Successfully processed Instagram post: {request.instagram_url}")

        return {
            "status": "success",
            "url": str(request.instagram_url),
            "author": raw_data.author,
            "caption_length": len(raw_data.caption),
            "media_count": len(raw_data.media_urls)
        }

    except Exception as exc:
        logger.error(f"Failed to process Instagram post {request_data.get('instagram_url', 'unknown')}: {exc}")

        # Retry with exponential backoff
        retry_countdown = 2 ** self.request.retries * 60  # 60s, 120s, 240s
        raise self.retry(countdown=retry_countdown, exc=exc)

def publish_raw_recipe_data(raw_data: dict):
    """
    Publish extracted data to raw_recipe_data queue as plain JSON.

    This publishes directly to RabbitMQ (not via Celery) so that the
    TypeScript Recipe Schema Converter can consume plain JSON messages.

    Messages are persisted (delivery_mode=2) and the queue is durable,
    so messages survive until consumed.
    """
    try:
        logger.info(f"Publishing raw recipe data for post: {raw_data.get('url', 'unknown')}")

        # Validate the data structure
        validated_data = RawRecipeData(**raw_data)

        # Connect to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()

        # Declare durable queue (survives RabbitMQ restart)
        channel.queue_declare(queue='raw_recipe_data', durable=True)

        # Prepare message with full data
        message = validated_data.model_dump()

        # Serialize datetime to ISO format
        message['timestamp'] = validated_data.timestamp.isoformat()

        # Publish message with persistence
        channel.basic_publish(
            exchange='',
            routing_key='raw_recipe_data',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json'
            )
        )

        connection.close()

        logger.info(f"Successfully published recipe data to RabbitMQ: {validated_data.url}")

    except Exception as exc:
        logger.error(f"Failed to publish raw recipe data: {exc}")
        raise