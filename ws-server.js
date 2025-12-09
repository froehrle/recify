import { WebSocketServer } from "ws";

const PORT = 8080;

export default function startWebSocketServer() {
  const wss = new WebSocketServer({ port: PORT });

  wss.on("connection", function connection(ws) {
    console.log("Client connected");

    // Messages from Client → RabbitMQ
    ws.on("message", async (msg) => {
      try {
        const payload = JSON.parse(msg.toString());
        // TODO: Hier Funktionen aus send.js aufrufen
        await channel.sendToQueue(
          QUEUE_NAME,
          Buffer.from(JSON.stringify(payload))
        );
        console.log("[RabbitMQ] sent message from client:", payload);
      } catch (err) {
        console.error("Error handling client message:", err);
      }
    });

    ws.on("error", console.error);

    ws.on("close", () => {
      console.log("Client disconnected");
    });
  });

  console.log(`WebSocket server listening on ws://localhost:${PORT}`);

  return wss;
}
