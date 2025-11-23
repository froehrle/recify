FROM rabbitmq:3.11-management

# Download and install the delayed message exchange plugin
RUN apt-get update && \
    apt-get install -y curl && \
    curl -L https://github.com/rabbitmq/rabbitmq-delayed-message-exchange/releases/download/3.11.1/rabbitmq_delayed_message_exchange-3.11.1.ez \
        -o /opt/rabbitmq/plugins/rabbitmq_delayed_message_exchange-3.11.1.ez && \
    rabbitmq-plugins enable --offline rabbitmq_delayed_message_exchange && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*