# recify

A recipe management system with event-driven architecture for crawling, processing, and storing recipes from Instagram.

## Architecture Overview

The system follows an event-driven architecture using RabbitMQ as the central message broker:

```mermaid
graph TB
    subgraph "Data Sources"
        IG[Instagram Crawler]
    end

    subgraph "Message Broker"
        RMQ[RabbitMQ]
    end

    subgraph "Processing"
        RSC[Recipe Schema Converter]
    end

    subgraph "External Services"
        LLM[LLM API]
    end

    subgraph "Storage"
        DB[(MongoDB)]
    end

    subgraph "Backend"
        FC[Frontend Connector]
    end

    subgraph "Presentation"
        UI[Web UI]
    end

    IG -->|Publish: raw_recipe_data| RMQ
    RMQ -->|Consume: raw_recipe_data| RSC
    RSC <-->|API Request/Response| LLM
    RSC -->|Publish: converted_recipe| RMQ
    RMQ -->|Consume: converted_recipe| DB
    RMQ -->|Consume: converted_recipe| FC
    DB <-->|Query/Store| UI
    UI <-->|WebSocket| FC
    FC -->|Publish: crawl_requests| RMQ
    RMQ -->|Crawl command| IG

    style RMQ fill:#ff6b6b
    style IG fill:#4ecdc4
    style RSC fill:#45b7d1
    style LLM fill:#a29bfe
    style DB fill:#96ceb4
    style FC fill:#fd79a8
    style UI fill:#ffeaa7
```

## Components

### Instagram Crawler
Scrapes recipe content from Instagram and publishes raw data to RabbitMQ.

### RabbitMQ
Central message broker handling asynchronous communication between components.

### Recipe Schema Converter
Processes raw recipe data and converts it into a standardized schema format using an external LLM API for intelligent extraction and structuring.

### LLM API
External language model service accessed via API to parse and structure unstructured recipe data into standardized format.

### MongoDB
Persistent data storage for processed recipes.

### Frontend Connector
WebSocket server that bridges the Web UI and RabbitMQ. Receives crawl requests from the frontend via WebSocket and publishes them to RabbitMQ. Consumes converted recipes from RabbitMQ and forwards them to connected clients in real-time.

### Web UI
User interface for browsing recipes and triggering crawl operations.