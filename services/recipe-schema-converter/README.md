# Recipe Schema Converter Service

TypeScript-based RabbitMQ microservice that converts raw Instagram recipe data into structured schema.org/Recipe format using GitHub Models LLM.

## Overview

- **Input**: Consumes `RawRecipeData` from `raw_recipe_data` queue
- **Processing**: Uses GitHub Models (Azure OpenAI GPT-4o) to extract structured recipe information
- **Output**: Publishes `StructuredRecipe` (schema.org/Recipe format) to `structured_recipes` queue
- **Retry Logic**: 3 attempts with exponential backoff (30s, 60s, 120s)
- **Dead Letter**: Failed messages moved to `recipe_conversion_failed` queue

## Quick Start

### Prerequisites

- Bun runtime installed
- RabbitMQ running (via Docker Compose)
- GitHub Personal Access Token with `models:read` scope

### Setup

1. Install dependencies:
```bash
just install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN
```

3. Run the service:
```bash
# Development mode with hot reload
just dev

# Production mode
just worker
```

## Testing

### Run Integration Test

The integration test uses a real German tofu wrap recipe to validate the full conversion pipeline:

```bash
# Ensure GITHUB_TOKEN is set in your environment
export GITHUB_TOKEN=ghp_your_token_here

# Run the test
bun test tests/integration.test.ts
```

Expected output:
- Validates schema.org/Recipe structure
- Extracts ingredients (German text)
- Extracts cooking instructions
- Extracts recipe metadata (yield, times, etc.)
- Logs full structured output for inspection

## Environment Variables

### Required

- `GITHUB_TOKEN` - GitHub Personal Access Token for GitHub Models API

### Optional

- `LLM_MODEL` - Model to use (default: `azure-openai/gpt-4o`)
- `LLM_BASE_URL` - GitHub Models endpoint (default: `https://models.github.ai/inference`)
- `LLM_MAX_TOKENS` - Max completion tokens (default: `2048`)
- `RABBITMQ_URL` - RabbitMQ connection URL (default: `amqp://guest:guest@localhost:5672`)
- `PREFETCH_COUNT` - Message prefetch count (default: `1`)
- `MAX_RETRIES` - Max retry attempts (default: `3`)

## Docker

### Build and Run

```bash
# Build image
just build

# Run with Docker
just docker-run

# Or use Docker Compose
docker compose up recipe-schema-converter
```

## Architecture

### Message Flow

```
Instagram Scraper → [raw_recipe_data] → Recipe Converter → [structured_recipes] → Storage/API
                                              ↓ (on failure)
                                    [recipe_conversion_failed]
```

### Key Components

- **`src/converter.ts`** - LLM-based recipe extraction using GitHub Models
- **`src/worker.ts`** - RabbitMQ consumer/publisher with retry logic
- **`src/prompts.ts`** - LLM prompt engineering for recipe extraction
- **`src/config.ts`** - Environment-based configuration
- **`src/types/index.ts`** - TypeScript type definitions

## AsyncAPI Specification

The service follows AsyncAPI 3.0 specification:

```bash
# Validate spec
just validate-asyncapi

# View spec
cat asyncapi.yaml
```

## Justfile Commands

```bash
just install              # Install dependencies
just worker               # Run worker
just dev                  # Run with hot reload
just test                 # Run tests
just typecheck            # Type check
just validate-asyncapi    # Validate AsyncAPI spec
just build                # Build Docker image
just docker-run           # Run with Docker
```

## Output Schema

The service outputs schema.org/Recipe JSON-LD format:

```json
{
  "@context": "https://schema.org",
  "@type": "Recipe",
  "name": "Recipe Title",
  "description": "Brief description",
  "author": {
    "@type": "Person",
    "name": "username",
    "url": "https://www.instagram.com/username"
  },
  "datePublished": "2025-04-11T11:02:24",
  "image": ["https://..."],
  "recipeIngredient": ["400g tofu", "2 tbsp tomato paste", ...],
  "recipeInstructions": [
    {"@type": "HowToStep", "text": "Step 1"},
    {"@type": "HowToStep", "text": "Step 2"}
  ],
  "prepTime": "PT15M",
  "cookTime": "PT30M",
  "totalTime": "PT45M",
  "recipeYield": "2 servings",
  "recipeCategory": "main course",
  "recipeCuisine": "Mexican",
  "keywords": "tofu, vegan, wraps",
  "source_url": "https://www.instagram.com/p/...",
  "extraction_confidence": 0.85,
  "extraction_notes": null
}
```

## Error Handling

- **Transient Errors**: Retried up to 3 times with exponential backoff
- **Rate Limits**: Handled with longer retry delays
- **Parse Errors**: Moved to failed queue after max retries
- **Invalid Messages**: Logged and moved to failed queue

## Monitoring

Check service logs:
```bash
docker compose logs -f recipe-schema-converter
```

Inspect queues via RabbitScout UI:
```
http://localhost:3000
```

## Troubleshooting

### LLM API Errors

- Ensure `GITHUB_TOKEN` is valid and has `models:read` scope
- Check GitHub Models status at https://github.com/marketplace/models
- Verify rate limits aren't exceeded

### RabbitMQ Connection Issues

- Ensure RabbitMQ is running: `docker compose ps rabbitmq`
- Check connection URL in environment variables
- Verify network connectivity

### Low Extraction Confidence

- Check if caption contains clear recipe structure
- Review `extraction_notes` field in output
- Consider adjusting prompts in `src/prompts.ts`

## Development

### Type Checking

```bash
just typecheck
```

### Hot Reload

```bash
just dev
```

### Adding Features

1. Update types in `src/types/index.ts`
2. Modify AsyncAPI spec in `asyncapi.yaml`
3. Update converter logic in `src/converter.ts`
4. Rebuild AsyncAPI bundle: `just asyncapi-build` (from root)

## License

Apache 2.0