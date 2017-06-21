import glob
import redis
import time

from os import path

from ..broker import Broker, Consumer, MessageProxy
from ..common import current_millis, dq_name
from ..errors import ConnectionClosed
from ..message import Message


class RedisBroker(Broker):
    """A broker than can be used with Redis.

    Parameters:
      \**parameters(dict): Connection parameters are passed directly
        to :class:`redis.StrictRedis`.
    """

    def __init__(self, *, middleware=None, **parameters):
        super().__init__(middleware=middleware)

        self.queues = set()
        self.connection = redis.StrictRedis(**parameters)
        self._load_scripts()

    def consume(self, queue_name, prefetch=1, timeout=5000):
        return _RedisConsumer(self, queue_name, prefetch, timeout)

    def declare_queue(self, queue_name):
        if queue_name not in self.queues:
            self.emit_before("declare_queue", queue_name)
            self.queues.add(queue_name)
            self.emit_after("declare_queue", queue_name)

            delayed_name = dq_name(queue_name)
            self.delay_queues.add(delayed_name)
            self.emit_after("declare_delay_queue", delayed_name)

    def enqueue(self, message, *, delay=None):
        self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, message.queue_name)
        self.emit_before("enqueue", message, delay)

        queue_name = message.queue_name
        if delay is not None:
            queue_name = dq_name(queue_name)
            message.options["eta"] = current_millis() + delay

        self._enqueue(queue_name, message.message_id, message.encode())
        self.emit_after("enqueue", message, delay)

    def get_declared_queues(self):
        return self.queues.copy()

    def join(self, queue_name):
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests to
        wait for all the messages in a queue to be processed.

        Parameters:
          queue_name(str): The queue to wait on.
        """
        successes = 0
        while successes < 3:
            size = 0
            for queue_name in (queue_name, dq_name(queue_name)):
                size += self.connection.hlen(f"{queue_name}.msgs")

            if size == 0:
                successes += 1

            time.sleep(1)

    def _load_scripts(self):
        self.scripts = {name: self.connection.register_script(script) for name, script in _scripts.items()}

    def _enqueue(self, queue_name, message_id, message_data):
        self.scripts["enqueue"](args=[
            queue_name, message_id, message_data,
        ])

    def _fetch(self, queue_name, prefetch, timeout):
        return self.scripts["fetch"](args=[queue_name, prefetch, timeout])

    def _ack(self, queue_name, message_id):
        # TODO: Periodically scan for unacked messages.
        return self.scripts["ack"](args=[queue_name, message_id])

    def _nack(self, queue_name, message_id):
        # TODO: Add dead letter queue.
        return self.scripts["ack"](args=[queue_name, message_id])


class _RedisConsumer(Consumer):
    def __init__(self, broker, queue_name, prefetch, timeout):
        self.message_cache = []
        self.misses = 0

        self.broker = broker
        self.queue_name = queue_name
        self.prefetch = prefetch
        self.timeout = timeout

    def __next__(self):
        try:
            if not self.message_cache:
                self.message_cache = self.broker._fetch(
                    queue_name=self.queue_name,
                    prefetch=self.prefetch,
                    timeout=self.timeout,
                )

            if self.message_cache:
                self.misses = 0
                data = self.message_cache.pop(0)
                message = Message.decode(data)
                return _RedisMessage(self.broker, message)

            else:
                time.sleep(min(self.timeout / 1000, 0.0125 * 2 ** self.misses))
                self.misses = min(self.misses + 1, 4)
                return None
        except redis.ConnectionError as e:
            raise ConnectionClosed(e)


class _RedisMessage(MessageProxy):
    def __init__(self, broker, message):
        super().__init__(message)
        self._broker = broker

    def acknowledge(self):
        self._broker._ack(self.queue_name, self.message_id)

    def reject(self):
        self._broker._nack(self.queue_name, self.message_id)


_scripts = {}
_scripts_path = path.join(path.abspath(path.dirname(__file__)), "redis")
for filename in glob.glob(path.join(_scripts_path, "*.lua")):
    script_name, _ = path.splitext(path.basename(filename))
    with open(filename, "rb") as f:
        _scripts[script_name] = f.read()
