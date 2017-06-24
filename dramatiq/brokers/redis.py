import glob
import redis
import time

from os import path
from threading import Thread

from ..broker import Broker, Consumer, MessageProxy
from ..common import compute_backoff, current_millis, dq_name, xq_name
from ..errors import ConnectionClosed
from ..logging import get_logger
from ..message import Message


class RedisBroker(Broker):
    """A broker than can be used with Redis.

    Parameters:
      middleware(list[Middleware])
      namespace(str): The str with which to prefix all Redis keys.
      requeue_deadline(int): The amount of time, in milliseconds,
        messages are allowed to be unacked for.
      requeue_interval(int): The interval, in milliseconds, at which
        unacked messages should be checked.
      \**parameters(dict): Connection parameters are passed directly
        to :class:`redis.StrictRedis`.
    """

    def __init__(self, *, middleware=None, namespace="dramatiq", requeue_deadline=86400000, requeue_interval=3600000, **parameters):  # noqa
        super().__init__(middleware=middleware)

        self.namespace = namespace
        self.dead_message_ttl = 86400 * 7 * 1000
        self.requeue_deadline = requeue_deadline
        self.requeue_interval = requeue_interval
        self.queues = set()
        self.client = client = redis.StrictRedis(**parameters)
        self.scripts = {name: client.register_script(script) for name, script in _scripts.items()}
        self.watcher = _RedisWatcher(self, interval=requeue_interval)

    def close(self):
        self.watcher.stop()

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
        queue_name = message.queue_name
        if delay is not None:
            queue_name = dq_name(queue_name)
            message.options["eta"] = current_millis() + delay

        self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, queue_name)
        self.emit_before("enqueue", queue_name, message, delay)
        self._enqueue(queue_name, message.message_id, message.encode())
        self.emit_after("enqueue", queue_name, message, delay)

    def get_declared_queues(self):
        return self.queues.copy()

    def join(self, queue_name):
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests to
        wait for all the messages in a queue to be processed.

        Parameters:
          queue_name(str): The queue to wait on.
        """
        while True:
            size = 0
            for name in (queue_name, dq_name(queue_name)):
                size += self.client.hlen(self._add_namespace(f"{name}.msgs"))

            if size == 0:
                return

            time.sleep(1)

    def _add_namespace(self, queue_name):
        return f"{self.namespace}:{queue_name}"

    def _enqueue(self, queue_name, message_id, message_data):
        enqueue = self.scripts["enqueue"]
        queue_name = self._add_namespace(queue_name)
        enqueue(args=[queue_name, message_id, message_data])

    def _fetch(self, queue_name, prefetch):
        fetch = self.scripts["fetch"]
        timestamp = current_millis()
        queue_name = self._add_namespace(queue_name)
        return fetch(args=[queue_name, prefetch, timestamp])

    def _ack(self, queue_name, message_id):
        ack = self.scripts["ack"]
        queue_name = self._add_namespace(queue_name)
        ack(args=[queue_name, message_id])

    def _nack(self, queue_name, message_id):
        # This is a little janky, but we can expect the naming
        # convention not to change.  Additionally, users aren't
        # allowed to have periods in their queues' names.
        if queue_name.endswith(".DQ"):
            xqueue_name = xq_name(queue_name[:-3])
        else:
            xqueue_name = xq_name(queue_name)

        # TODO: Clean up dead messages.
        nack = self.scripts["nack"]
        timestamp = current_millis()
        queue_name = self._add_namespace(queue_name)
        xqueue_name = self._add_namespace(xqueue_name)
        nack(args=[queue_name, xqueue_name, message_id, timestamp])

    def _requeue(self):
        requeue = self.scripts["requeue"]
        timestamp = current_millis() - self.requeue_deadline
        queue_names = self.get_declared_queues() | self.get_declared_delay_queues()
        queue_names = [self._add_namespace(queue_name) for queue_name in queue_names]
        requeue(args=[timestamp], keys=queue_names)

    def _cleanup(self):
        cleanup = self.scripts["cleanup"]
        timestamp = current_millis() - self.dead_message_ttl
        queue_names = map(xq_name, self.get_declared_queues())
        queue_names = [self._add_namespace(queue_name) for queue_name in queue_names]
        cleanup(args=[timestamp], keys=queue_names)


class _RedisWatcher(Thread):
    """Runs the Redis requeue and cleanup scripts on a timer in order
    to salvage unacked messages and drop old dead-lettered messages.
    """

    def __init__(self, broker, *, interval=3600000):
        super().__init__(daemon=True)

        self.logger = get_logger(__name__, type(self))
        self.broker = broker
        self.interval = interval
        self.running = False
        self.start()

    def run(self):
        self.logger.debug("Starting watcher...")
        self.running = True
        while self.running:
            try:
                time.sleep(self.interval / 1000)

                self.logger.debug("Running requeue...")
                self.broker._requeue()

                self.logger.debug("Running cleanup...")
                self.broker._cleanup()
            except Exception:
                self.logger.warning("Requeue failed.", exc_info=True)

    def stop(self):
        self.logger.debug("Stopping watcher...")
        self.running = False


class _RedisConsumer(Consumer):
    def __init__(self, broker, queue_name, prefetch, timeout):
        self.message_cache = []
        self.message_refc = 0
        self.misses = 0

        self.broker = broker
        self.queue_name = queue_name
        self.prefetch = prefetch
        self.timeout = timeout

    def acknowledge(self, message_id):
        # The current queue might be different from message.queue_name
        # if the message has been delayed so we want to ack on the
        # current queue.
        self.broker._ack(self.queue_name, message_id)
        self.message_refc -= 1

    def reject(self, message_id):
        self.broker._nack(self.queue_name, message_id)
        self.message_refc -= 1

    def __next__(self):
        try:
            while True:
                try:
                    # This is a micro-optimization so we try the fast
                    # path first.  We assume there are messages in the
                    # cache and if there aren't, we go down the slow
                    # path of doing network IO.
                    data = self.message_cache.pop(0)
                    self.misses = 0

                    message = Message.decode(data)
                    return _RedisMessage(self, message)
                except IndexError:
                    # If there are fewer messages currently being
                    # processed than we're allowed to prefetch,
                    # prefetch up to that number of messages.
                    messages = []
                    if self.message_refc < self.prefetch:
                        self.message_cache = messages = self.broker._fetch(
                            queue_name=self.queue_name,
                            prefetch=self.prefetch - self.message_refc,
                        )

                    # Because we didn't get any messages, we should
                    # progressively long poll up to the idle timeout.
                    if not messages:
                        self.misses, backoff_ms = compute_backoff(self.misses, max_backoff=self.timeout)
                        time.sleep(backoff_ms / 1000)
                        return None

                    # Since we received some number of messages, we
                    # have to keep track of them.
                    self.message_refc += len(messages)
        except redis.ConnectionError as e:
            raise ConnectionClosed(e)


class _RedisMessage(MessageProxy):
    def __init__(self, consumer, message):
        super().__init__(message)
        self._consumer = consumer

    def acknowledge(self):
        self._consumer.acknowledge(self.message_id)

    def reject(self):
        self._consumer.reject(self.message_id)


_scripts = {}
_scripts_path = path.join(path.abspath(path.dirname(__file__)), "redis")
for filename in glob.glob(path.join(_scripts_path, "*.lua")):
    script_name, _ = path.splitext(path.basename(filename))
    with open(filename, "rb") as f:
        _scripts[script_name] = f.read()
