class DramatiqError(Exception):
    """Base class for all dramatiq errors.
    """


class BrokerError(DramatiqError):
    """Base class for broker-related errors.
    """


class ActorNotFound(BrokerError):
    """Raised when a message is sent to an actor that hasn't been declared.
    """


class QueueNotFound(BrokerError):
    """Raised when a message is sent to an queue that hasn't been declared.
    """
