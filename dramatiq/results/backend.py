import hashlib
import time

from ..common import compute_backoff, q_name
from .errors import ResultTimeout, ResultMissing

#: The default timeout for blocking get operations in milliseconds.
DEFAULT_TIMEOUT = 10000

#: The minimum amount of time in ms to wait between polls.
BACKOFF_FACTOR = 100

#: Canary value that is returned when a result hasn't been set yet.
Missing = type("Missing", (object,), {})()


class ResultBackend:
    """ABC for result backends.
    """

    def get_result(self, message, *, block=False, timeout=None):
        """Get a result from the backend.

        Parameters:
          message(Message)
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.

        Returns:
          object: The result.
        """
        timeout = timeout or DEFAULT_TIMEOUT
        end_time = time.monotonic() + timeout / 1000
        message_key = self.build_message_key(message)

        attempts = 0
        while True:
            data = self._get(message_key)
            if data is Missing and block:
                attempts, delay = compute_backoff(attempts, factor=BACKOFF_FACTOR)
                delay /= 1000
                if time.monotonic() + delay > end_time:
                    raise ResultTimeout(message)

                time.sleep(delay)
                continue

            elif data is Missing:
                raise ResultMissing(message)

            else:
                return data

    def store_result(self, message, result, ttl):
        """Store a result in the backend.

        Parameters:
          message(Message)
          result(object): Must be serializable.
          ttl(int): The maximum amount of time the result may be
            stored in the backend for.
        """
        message_key = self.build_message_key(message)
        return self._store(message_key, result, ttl)

    def build_message_key(self, message):
        """Given a message, return its globally-unique key.

        Parameters:
          message(Message)

        Returns:
          str
        """
        message_key = "%(namespace)s:%(queue_name)s:%(actor_name)s:%(message_id)s" % {
            "namespace": self.namespace,
            "queue_name": q_name(message.queue_name),
            "actor_name": message.actor_name,
            "message_id": message.message_id,
        }
        return hashlib.md5(message_key.encode("utf-8")).hexdigest()

    def _get(self, message_key):  # pragma: no cover
        """Get a result from the backend.
        """
        raise NotImplementedError

    def _store(self, message_key, result, ttl):  # pragma: no cover
        """Store a result in the backend.
        """
        raise NotImplementedError
