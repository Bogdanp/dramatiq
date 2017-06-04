class DramatiqError(Exception):  # pragma: no cover
    """Base class for all dramatiq errors.
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message) or repr(self.message)


class BrokerError(DramatiqError):
    """Base class for broker-related errors.
    """


class ActorNotFound(BrokerError):
    """Raised when a message is sent to an actor that hasn't been declared.
    """


class QueueNotFound(BrokerError):
    """Raised when a message is sent to an queue that hasn't been declared.
    """


class ConnectionError(BrokerError):
    """Base class for broker connection-related errors.
    """


class ConnectionFailed(ConnectionError):
    """Raised when a broker connection could not be opened.
    """


class ConnectionClosed(ConnectionError):
    """Raised when a broker connection is suddenly closed.
    """
