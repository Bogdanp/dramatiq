import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.middleware import AsyncIO

rabbitmq_broker = RabbitmqBroker(url="amqp://guest:guest@localhost:5672")

rabbitmq_broker.add_middleware(AsyncIO())

dramatiq.set_broker(rabbitmq_broker)

from tasks.bar import *  # !!! IT'S IMPORTANT !!!
from tasks.foo import *  # !!! IT'S IMPORTANT !!!
