import os
from dotenv import load_dotenv

load_dotenv()

# RabbitMQ Configuration
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'pyamqp://guest@localhost//')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'guest')

# Celery Configuration
CELERY_BROKER_URL = RABBITMQ_URL
CELERY_RESULT_BACKEND = None

# Instagram Configuration
INSTAGRAM_SESSION_FILE = os.getenv('INSTAGRAM_SESSION_FILE', 'session')
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')