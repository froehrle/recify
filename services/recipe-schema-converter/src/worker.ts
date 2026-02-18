/**
 * RabbitMQ worker for consuming raw recipe data and publishing structured recipes.
 */

import * as amqp from "amqplib";
import { config } from "./config.ts";
import { RecipeConverter } from "./converter.ts";
import type { RawRecipeData } from "./types/index.ts";

export class RecipeConverterWorker {
  private connection: amqp.Connection | null = null;
  private channel: amqp.Channel | null = null;
  private converter: RecipeConverter;

  constructor() {
    this.converter = new RecipeConverter();
  }

  /**
   * Connect to RabbitMQ and set up channels/queues.
   */
  async connect(): Promise<void> {
    console.log(`Connecting to RabbitMQ at ${config.rabbitmq.host}...`);

    this.connection = await amqp.connect(config.rabbitmq.url);
    this.channel = await this.connection.createChannel();

    // Declare queues
    await this.channel.assertQueue(config.queues.input, { durable: true });
    await this.channel.assertQueue(config.queues.output, { durable: true });
    await this.channel.assertQueue(config.queues.failed, { durable: true });

    // Set prefetch for fair dispatch
    await this.channel.prefetch(config.worker.prefetchCount);

    console.log("Connected to RabbitMQ successfully");
  }

  /**
   * Start consuming messages.
   */
  async start(): Promise<void> {
    console.log("Starting Recipe Schema Converter Worker...");

    // Setup graceful shutdown
    process.on("SIGINT", () => this.stop());
    process.on("SIGTERM", () => this.stop());

    await this.connect();

    console.log(`Waiting for messages from '${config.queues.input}' queue...`);

    await this.channel!.consume(
      config.queues.input,
      (msg) => this.processMessage(msg),
      { noAck: false }
    );
  }

  /**
   * Process a single message.
   */
  private async processMessage(msg: amqp.ConsumeMessage | null): Promise<void> {
    if (!msg || !this.channel) return;

    let rawData: RawRecipeData | null = null;

    try {
      rawData = JSON.parse(msg.content.toString()) as RawRecipeData;
      console.log(`Processing recipe from: ${rawData.url}`);

      // Convert using LLM
      const structuredRecipe = await this.converter.convert(rawData);

      // Publish to output queue
      this.channel.sendToQueue(
        config.queues.output,
        Buffer.from(JSON.stringify(structuredRecipe)),
        { persistent: true, contentType: "application/json" }
      );

      // Acknowledge successful processing
      this.channel.ack(msg);
      console.log(
        `Successfully converted: ${rawData.url} (confidence: ${structuredRecipe.extraction_confidence})`
      );
    } catch (error) {
      console.error("Error processing message:", error);

      const retryCount = this.getRetryCount(msg);

      if (retryCount < config.worker.maxRetries) {
        await this.scheduleRetry(msg, retryCount);
      } else {
        await this.moveToFailedQueue(msg, rawData, error);
      }

      // Acknowledge to remove from original queue
      this.channel.ack(msg);
    }
  }

  /**
   * Get the current retry count from message headers.
   */
  private getRetryCount(msg: amqp.ConsumeMessage): number {
    const headers = msg.properties.headers || {};
    return (headers["x-retry-count"] as number) || 0;
  }

  /**
   * Schedule a retry with exponential backoff.
   */
  private async scheduleRetry(
    msg: amqp.ConsumeMessage,
    retryCount: number
  ): Promise<void> {
    const delay =
      config.worker.retryDelays[
        Math.min(retryCount, config.worker.retryDelays.length - 1)
      ];

    console.log(
      `Scheduling retry ${retryCount + 1}/${config.worker.maxRetries} in ${delay / 1000}s`
    );

    // Simple retry: wait and republish to input queue
    // For production, consider using a delayed message exchange plugin
    setTimeout(() => {
      this.channel?.sendToQueue(config.queues.input, msg.content, {
        persistent: true,
        contentType: "application/json",
        headers: {
          ...msg.properties.headers,
          "x-retry-count": retryCount + 1,
        },
      });
    }, delay);
  }

  /**
   * Move failed message to dead letter queue.
   */
  private async moveToFailedQueue(
    msg: amqp.ConsumeMessage,
    rawData: RawRecipeData | null,
    error: unknown
  ): Promise<void> {
    const failedMessage = {
      original_message: rawData || JSON.parse(msg.content.toString()),
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      retry_count: this.getRetryCount(msg),
      failed_at: new Date().toISOString(),
    };

    this.channel?.sendToQueue(
      config.queues.failed,
      Buffer.from(JSON.stringify(failedMessage)),
      { persistent: true, contentType: "application/json" }
    );

    console.log(`Message moved to failed queue after ${config.worker.maxRetries} retries`);
  }

  /**
   * Gracefully stop the worker.
   */
  async stop(): Promise<void> {
    console.log("Shutting down worker...");

    if (this.channel) {
      await this.channel.close();
    }
    if (this.connection) {
      await this.connection.close();
    }

    console.log("Worker stopped");
    process.exit(0);
  }
}