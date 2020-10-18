import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker


def setup_broker():
    print("Setting up broker...")
    broker = RabbitmqBroker()
    dramatiq.set_broker(broker)
