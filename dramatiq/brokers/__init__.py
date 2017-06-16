import warnings

from .stub import StubBroker  # noqa

try:
    from .rabbitmq import RabbitmqBroker  # noqa
except ImportError as e:
    warnings.warn(
        "RabbitmqBroker not available.  `pip install dramatiq[rabbitmq]` to get RabbitMQ support.",
        category=RuntimeWarning, stacklevel=2,
    )
