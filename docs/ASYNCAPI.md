# AsyncAPI Setup and Usage

This document describes the AsyncAPI setup for the Recify project, including how to bundle specifications, generate code, and use the generated client for publishing and consuming messages.

## Overview

The project uses AsyncAPI to:
- Define event-driven API contracts for microservices
- Automatically generate Node.js client code for RabbitMQ communication
- Ensure type-safe message publishing and consumption

## Project Structure

```
recify/
├── services/
│   └── instagram-scraper/
│       └── asyncapi.yaml          # Service-specific AsyncAPI spec
├── scripts/
│   └── bundle-asyncapi.sh          # Auto-discovers and bundles all specs
├── generated/
│   └── asyncapi/                   # Generated client code
│       ├── src/
│       │   ├── api/
│       │   │   ├── handlers/       # Message handlers
│       │   │   ├── routes/         # Channel routes
│       │   │   └── index.js        # Main client
│       │   └── lib/                # Utilities
│       └── package.json
├── examples/
│   ├── asyncapi-consumer.ts        # Example consumer implementation
│   └── asyncapi-publisher.ts       # Example publisher implementation
└── asyncapi-bundled.yaml           # Bundled specification (all services)
```

## Quick Start

### 1. Bundle and Generate Code

```bash
# Bundle all AsyncAPI specs from services/
just asyncapi-bundle

# Generate Node.js client code
just asyncapi-generate

# Or do both at once
just asyncapi-build
```

Alternatively using bun directly:
```bash
bun run asyncapi:build
```

### 2. Install Generated Dependencies

The generated code has its own dependencies:
```bash
cd generated/asyncapi
npm install
```

## Usage

### Publishing Messages

```typescript
const { client } = require('./generated/asyncapi/src/api');

// Initialize the client
await new Promise<void>((resolve) => {
  client.init();
  setTimeout(resolve, 2000); // Wait for connection
});

// Publish a crawl request
await client.app.send({
  instagram_url: 'https://www.instagram.com/p/ABC123/',
  request_id: 'req-001',
  priority: 5
}, {}, 'crawl_requests');

// Publish raw recipe data
await client.app.send({
  url: 'https://www.instagram.com/p/ABC123/',
  caption: 'Delicious pasta recipe...',
  media_urls: ['https://...'],
  author: 'chef_mario',
  timestamp: new Date().toISOString(),
  hashtags: ['pasta', 'recipe'],
  mentions: []
}, {}, 'raw_recipe_data');
```

See `examples/asyncapi-publisher.ts` for a complete example.

### Consuming Messages

```typescript
const { client } = require('./generated/asyncapi/src/api');

// Register handler for crawl requests
client.registerCrawlInstagramPostMiddleware(async (message) => {
  console.log('Received:', message.payload);

  const { instagram_url, request_id, priority } = message.payload;

  // Your business logic here
  await processInstagramUrl(instagram_url);
});

// Start consuming
client.init();
```

See `examples/asyncapi-consumer.ts` for a complete example.

## Available Commands

### Using Just (recommended)

```bash
just asyncapi-bundle      # Bundle specs from services/
just asyncapi-generate    # Generate code from bundle
just asyncapi-build       # Bundle + generate
```

### Using Bun/npm scripts

```bash
bun run asyncapi:bundle
bun run asyncapi:generate
bun run asyncapi:build
```

## Adding New Services

When you add a new microservice with AsyncAPI specifications:

1. Create your AsyncAPI spec in the service directory:
   ```
   services/your-service/asyncapi.yaml
   ```

2. Run the bundle command - it will automatically discover all specs:
   ```bash
   just asyncapi-bundle
   ```

3. Regenerate the client code:
   ```bash
   just asyncapi-generate
   ```

The bundling script (`scripts/bundle-asyncapi.sh`) automatically finds all `asyncapi.yaml` or `asyncapi.yml` files in the `services/` directory.

## Configuration

### RabbitMQ Connection

The generated code uses configuration from `generated/asyncapi/config/common.yml`. You can customize:
- Broker host and port
- Authentication credentials
- Connection options

Example configuration:
```yaml
app:
  name: Instagram Scraper Service
  version: 1.0.0

broker:
  amqp:
    url: amqp://localhost:5672
```

### Environment Variables

You can also use environment variables in your code:
```bash
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
export RABBITMQ_USER=guest
export RABBITMQ_PASS=guest
```

## Generated Client API

### Client Object

```typescript
const { client } = require('./generated/asyncapi/src/api');
```

**Properties:**
- `client.app` - HermesJS application instance
- `client.init()` - Initialize and start the client

**Methods:**
- `client.registerCrawlInstagramPostMiddleware(handler)` - Register consumer handler
- `client.registerPublishRawRecipeDataMiddleware(handler)` - Register publisher middleware
- `client.app.send(message, headers, channel)` - Publish a message

## Message Schemas

### CrawlRequest

Published to: `crawl_requests`

```typescript
{
  instagram_url: string;      // Required: Instagram post/reel URL
  request_id?: string;        // Optional: Request identifier
  priority?: number;          // Optional: 1-10 (default: 1)
}
```

### RawRecipeData

Published to: `raw_recipe_data`

```typescript
{
  url: string;                    // Instagram post URL
  caption: string;                // Post caption
  media_urls: string[];           // Image/video URLs
  author: string;                 // Instagram username
  timestamp: string;              // ISO 8601 date-time
  hashtags: string[];             // Hashtags (without #)
  mentions: string[];             // Mentions (without @)
  likes_count?: number | null;    // Like count
  comments_count?: number | null; // Comment count
  author_top_comment?: string | null; // Top author comment
}
```

## Troubleshooting

### Connection Issues

If you can't connect to RabbitMQ:
1. Ensure RabbitMQ is running: `docker ps`
2. Check connection config in `generated/asyncapi/config/common.yml`
3. Verify network connectivity

### Generation Errors

If code generation fails:
1. Validate your AsyncAPI spec: `asyncapi validate services/your-service/asyncapi.yaml`
2. Check that the `server` parameter matches a server in your spec
3. Ensure all `$ref` references are valid

### Missing Dependencies

If you get module errors:
```bash
cd generated/asyncapi
npm install
```

## Resources

- [AsyncAPI Documentation](https://www.asyncapi.com/docs)
- [AsyncAPI CLI](https://github.com/asyncapi/cli)
- [Node.js Template](https://github.com/asyncapi/nodejs-template)
- [HermesJS Framework](https://github.com/hermesjs/hermesjs)