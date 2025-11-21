/**
 * Example consumer implementation using generated AsyncAPI code
 *
 * This demonstrates how to consume messages from the crawl_requests queue
 * and process them using the generated client.
 */

// Import the generated client
// Note: The generated code is CommonJS, so we use require
const { client } = require('../generated/asyncapi/src/api');

/**
 * Handler for processing crawl requests
 * This middleware will be called for each message received on the crawl_requests channel
 */
async function handleCrawlRequest(message: any) {
  console.log('Received crawl request:', JSON.stringify(message, null, 2));

  const payload = message.payload;

  // Your business logic here
  console.log(`Processing Instagram URL: ${payload.instagram_url}`);
  console.log(`Request ID: ${payload.request_id || 'N/A'}`);
  console.log(`Priority: ${payload.priority || 1}`);

  // Example: You could call your instagram scraper here
  // const result = await scrapeInstagramPost(payload.instagram_url);

  // After processing, you might want to publish the result
  // See asyncapi-publisher.ts for how to publish messages
}

// Register the middleware handler for crawl requests
client.registerCrawlInstagramPostMiddleware(handleCrawlRequest);

// Start the client
console.log('Starting AsyncAPI consumer...');
client.init();

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down consumer...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\nShutting down consumer...');
  process.exit(0);
});