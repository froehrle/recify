import startWebSocketServer from "./ws-server.js";

import { amqp } from "amqplib";

const RABBIT_MQ_URL = process.env.RABBIT_URL || "amqp://localhost";
const QUEUE_NAME = "crawlRequests";

(async () => {
  // 1. Connect RabbitMQ
  const connection = await amqp.connect(RABBIT_MQ_URL);
  const channel = await connection.createChannel();
  await channel.assertQueue(QUEUE_NAME);

  console.log("[RabbitMQ] connected, queue:", QUEUE_NAME);

  // 2. Start WebSocket server
  startWebSocketServer();
  console.log("WebSocket server started");
})();

// ws.on("message", function message(data) {
//   console.log("Received: %s", data);
// });
