from celery import Celery
from config import RABBITMQ_URL

app = Celery('instagram-scraper')
app.conf.update(
    broker_url=RABBITMQ_URL,
    result_backend=None,  # No result storage needed
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.crawl_instagram_post': {'queue': 'crawl_requests'},
        'tasks.publish_raw_recipe_data': {'queue': 'raw_recipe_data'},
    },
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Acknowledge after task completion
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
)

# Auto-discover tasks
app.autodiscover_tasks(['tasks'])