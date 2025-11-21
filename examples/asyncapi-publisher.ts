/**
 * Example publisher implementation using generated AsyncAPI code
 *
 * This demonstrates how to publish messages to RabbitMQ queues
 * using the generated client.
 */

// Import the generated client
const { client } = require('../generated/asyncapi/src/api');

/**
 * Example function to publish a crawl request
 */
async function publishCrawlRequest(instagramUrl: string, requestId?: string, priority?: number) {
  const message = {
    instagram_url: instagramUrl,
    request_id: requestId,
    priority: priority || 1
  };

  console.log('Publishing crawl request:', JSON.stringify(message, null, 2));

  // Send the message to the crawl_requests queue
  await client.app.send(message, {}, 'crawl_requests');

  console.log('✓ Message published successfully');
}

/**
 * Example function to publish raw recipe data
 */
async function publishRawRecipeData(data: {
  url: string;
  caption: string;
  media_urls: string[];
  author: string;
  timestamp: string;
  hashtags: string[];
  mentions: string[];
  likes_count?: number | null;
  comments_count?: number | null;
  author_top_comment?: string | null;
}) {
  console.log('Publishing raw recipe data:', JSON.stringify(data, null, 2));

  // Send the message to the raw_recipe_data queue
  await client.app.send(data, {}, 'raw_recipe_data');

  console.log('✓ Raw recipe data published successfully');
}

// Example usage
async function main() {
  // Initialize the client
  await new Promise<void>((resolve) => {
    client.init();
    setTimeout(resolve, 2000); // Wait for connection
  });

  // Example 1: Publish a crawl request
  await publishCrawlRequest(
    'https://www.instagram.com/p/ABC123DEF456/',
    'req-12345',
    5
  );

  // Example 2: Publish raw recipe data (simulated result)
  await publishRawRecipeData({
    url: 'https://www.instagram.com/p/ABC123DEF456/',
    caption: 'Delicious homemade pasta! 🍝\n\nIngredients:\n- 400g flour\n- 4 eggs',
    media_urls: [
      'https://instagram.com/image1.jpg',
      'https://instagram.com/image2.jpg'
    ],
    author: 'chef_mario',
    timestamp: new Date().toISOString(),
    hashtags: ['pasta', 'homemade', 'recipe'],
    mentions: ['foodblogger'],
    likes_count: 1250,
    comments_count: 42,
    author_top_comment: 'Thanks for all the love! Recipe details in bio!'
  });

  // Close after publishing
  setTimeout(() => {
    console.log('Closing connection...');
    process.exit(0);
  }, 1000);
}

// Run the example if this file is executed directly
if (require.main === module) {
  main().catch(console.error);
}

// Export functions for use in other modules
export { publishCrawlRequest, publishRawRecipeData };