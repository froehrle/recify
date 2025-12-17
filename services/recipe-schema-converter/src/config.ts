/**
 * Configuration management for the Recipe Schema Converter service.
 */

import "dotenv/config";

export const config = {
  rabbitmq: {
    url: process.env.RABBITMQ_URL || "amqp://guest:guest@localhost:5672",
    host: process.env.RABBITMQ_HOST || "localhost",
    port: parseInt(process.env.RABBITMQ_PORT || "5672", 10),
    user: process.env.RABBITMQ_USER || "guest",
    pass: process.env.RABBITMQ_PASS || "guest",
  },

  llm: {
    apiKey: process.env.GITHUB_TOKEN || "",
    baseUrl: process.env.LLM_BASE_URL || "https://models.github.ai/inference",
    model: process.env.LLM_MODEL || "azure-openai/gpt-4o",
    maxTokens: parseInt(process.env.LLM_MAX_TOKENS || "2048", 10),
    timeout: parseInt(process.env.LLM_TIMEOUT || "60000", 10),
  },

  queues: {
    input: "raw_recipe_data",
    output: "structured_recipes",
    failed: "recipe_conversion_failed",
  },

  worker: {
    prefetchCount: parseInt(process.env.PREFETCH_COUNT || "1", 10),
    maxRetries: parseInt(process.env.MAX_RETRIES || "3", 10),
    retryDelays: [30_000, 60_000, 120_000] as const,
  },
} as const;