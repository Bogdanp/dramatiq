import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.middleware import CurrentMessage

# Set up Broker (and any custom Middleware)
rabbitmq_broker = RabbitmqBroker(url="amqp://guest:guest@localhost:5672")
rabbitmq_broker.add_middleware(CurrentMessage())

# Declare your Broker.
# IMPORTANT: This must run before importing any module that uses the @actor decorator.
# This is because @actor will immediately look up the Broker to associate the Actor with it.
dramatiq.set_broker(rabbitmq_broker)
