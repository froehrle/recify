from celeryapp import app
from instagram_crawler import InstagramCrawler
from models import CrawlRequest, RawRecipeData
import json
import logging

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

        # Publish to raw_recipe_data queue
        publish_raw_recipe_data.delay(raw_data.model_dump())

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

@app.task(name='publish_raw_recipe_data')
def publish_raw_recipe_data(raw_data: dict):
    """
    Publish extracted data to raw_recipe_data queue

    This task represents publishing the data to the next service in the pipeline.
    In a real implementation, this would send the data to the Recipe Schema Converter.
    """
    try:
        logger.info(f"Publishing raw recipe data for post: {raw_data.get('url', 'unknown')}")

        # Validate the data structure
        validated_data = RawRecipeData(**raw_data)

        # Here you would publish to the actual raw_recipe_data queue
        # For now, we just log the successful processing
        logger.info(f"Successfully published recipe data: {validated_data.url}")

        return {
            "status": "published",
            "url": validated_data.url,
            "timestamp": validated_data.timestamp.isoformat()
        }

    except Exception as exc:
        logger.error(f"Failed to publish raw recipe data: {exc}")
        raise