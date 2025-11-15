# Instagram Scraper Commands

# Install dependencies for instagram-scraper service
install-instagram-scraper:
    cd services/instagram-scraper && uv sync --dev

# Run tests for instagram-scraper service
test-instagram-scraper:
    cd services/instagram-scraper && uv run pytest

# Run integration tests only for instagram-scraper service
test-instagram-scraper-integration:
    cd services/instagram-scraper && uv run pytest tests/test_integration.py -v

# Run unit tests only for instagram-scraper service
test-instagram-scraper-unit:
    cd services/instagram-scraper && uv run pytest tests/test_crawler.py -v

# Create Instagram session file for authentication
create-instagram-session:
    cd services/instagram-scraper && uv run python create_session.py

# Start RabbitMQ for local development
start-rabbitmq:
    cd services/instagram-scraper && docker-compose up rabbitmq -d

# Start Celery worker for instagram-scraper service
start-instagram-worker:
    cd services/instagram-scraper && uv run celery -A celeryapp worker --loglevel=info

# Monitor Celery with Flower for instagram-scraper service
monitor-instagram-worker:
    cd services/instagram-scraper && uv run celery -A celeryapp flower

# Stop all Docker containers
stop-containers:
    docker-compose down

# Build and start all services
start-all:
    cd services/instagram-scraper && docker-compose up --build -d

# View RabbitMQ management interface (http://localhost:15672)
rabbitmq-ui:
    @echo "RabbitMQ Management UI: http://localhost:15672"
    @echo "Username: guest"
    @echo "Password: guest"