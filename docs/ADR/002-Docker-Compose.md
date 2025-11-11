---
title: '002: Docker and Docker Compose for Development and Deployment'
---

## Status

Accepted

## Context

Recify is built with an event-driven architecture consisting of multiple components:
- Instagram Crawler
- Recipe Schema Converter
- RabbitMQ (message broker)
- MongoDB (database)
- Web UI

### Challenges

1. **Environment Consistency**: Each component has different runtime requirements (Python, Node.js, message broker, database)
2. **Local Development**: Developers need to run all services locally for testing end-to-end workflows
3. **Dependency Management**: RabbitMQ and MongoDB need to be running before application components start
4. **Onboarding**: New team members should be able to get the entire system running quickly
5. **Deployment**: We need consistent deployments across development, staging, and production

### Alternatives Considered

- **Manual Installation**: Each developer installs all dependencies locally - too much setup overhead
- **Virtual Machines**: Too heavy and resource-intensive for local development
- **Kubernetes**: Overkill for a 3-person team and adds unnecessary complexity
- **Individual Docker Containers**: Manual container management is error-prone without orchestration

## Decision

We will use **Docker with Docker Compose** for both development and deployment:

### Docker Containers

Each component runs in its own container:
- `recify-crawler`: Instagram crawler service
- `recify-converter`: Recipe schema converter service
- `recify-ui`: Web UI application
- `rabbitmq`: Message broker (official RabbitMQ image)
- `mongodb`: Database (official MongoDB image)

### Docker Compose Configuration

Single `docker-compose.yml` defines the entire stack:

```yaml
version: '3.8'

services:
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"      # AMQP
      - "15672:15672"    # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: recify
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: recify
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongo_data:/data/db

  crawler:
    build: ./services/crawler
    depends_on:
      - rabbitmq
    environment:
      RABBITMQ_URL: amqp://rabbitmq:5672

  converter:
    build: ./services/converter
    depends_on:
      - rabbitmq
    environment:
      RABBITMQ_URL: amqp://rabbitmq:5672
      LLM_API_KEY: ${LLM_API_KEY}

  ui:
    build: ./services/ui
    ports:
      - "3000:3000"
    depends_on:
      - mongodb
    environment:
      MONGO_URL: mongodb://mongodb:27017/recify

volumes:
  rabbitmq_data:
  mongo_data:
```

### Development Workflow

1. **First-time setup**:
   ```bash
   cp .env.example .env
   # Edit .env with credentials
   docker compose up -d
   ```

2. **Daily development**:
   ```bash
   docker compose up        # Start all services
   docker compose logs -f   # Watch logs
   docker compose down      # Stop all services
   ```

3. **Rebuild after changes**:
   ```bash
   docker compose up --build
   ```

4. **Individual service development**:
   ```bash
   docker compose up rabbitmq mongodb  # Start dependencies only
   # Run your service locally for faster iteration
   ```

### Production Deployment

- Use the same `docker-compose.yml` with production overrides
- Environment-specific configs via `docker-compose.prod.yml`
- Secrets managed through environment variables or secret management service

## Consequences

### Benefits

1. **Consistency**: Same environment across all developer machines and deployment environments
2. **Fast Onboarding**: New developers run 2 commands to get everything working
3. **Isolation**: Each service runs independently, avoiding port and dependency conflicts
4. **Easy Testing**: Spin up entire stack for integration testing with one command
5. **Service Discovery**: Services reference each other by service name (e.g., `rabbitmq:5672`)
6. **Volume Persistence**: Data persists between container restarts
7. **Dependency Management**: `depends_on` ensures services start in correct order

### Trade-offs

1. **Docker Learning Curve**: Team needs to learn Docker basics
2. **Resource Usage**: Running all containers requires adequate RAM (~4GB minimum)
3. **Slower Builds**: Initial image builds take time (mitigated by layer caching)
4. **Debugging**: Slightly more complex than running processes directly (but Docker logs help)

### Guidelines

- Always use `.env` file for secrets (never commit it)
- Use health checks in production `docker-compose.prod.yml`
- Tag images with version numbers for production deployments
- Keep Dockerfiles simple and leverage multi-stage builds
- Use `.dockerignore` to avoid copying unnecessary files
- Document any special Docker commands in project README