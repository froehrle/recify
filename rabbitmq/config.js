import amqp from "amqplib/callback_api.js";

export default async function createRabbitConnection() {
  // TODO: Durch process.env.RABBITMQ_URL ersetzen?
  const connection = await amqp.connect("amqp://localhost", function (error) {
    if (error) {
      throw error;
    }
  });

  const channel = await connection.createChannel(function (error) {
    if (error) {
      throw error;
    }
  });

  console.log("[RabbitMQ] connected");

  return { connection, channel };
}
