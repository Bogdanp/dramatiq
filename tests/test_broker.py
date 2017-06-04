import dramatiq
import dramatiq.broker


def test_broker_uses_rabbitmq_if_not_set():
    # Given that no global broker is set
    dramatiq.broker.global_broker = None

    # If I try to get the global broker
    broker = dramatiq.get_broker()

    # I expect it to be a RabbitmqBroker instance
    assert isinstance(broker, dramatiq.brokers.RabbitmqBroker)
