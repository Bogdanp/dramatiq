import glob
import redis
import time

from os import path
from threading import Thread
from uuid import uuid4

from ..broker import Broker, Consumer, MessageProxy
from ..common import compute_backoff, current_millis, dq_name, xq_name
from ..errors import ConnectionClosed
from ..logging import get_logger
from ..message import Message

#: The amount of time in milliseconds that dead-lettered messages are
#: kept in Redis for.
DEFAULT_DEAD_MESSAGE_TTL = 86400000 * 7

#: The default amount of time to wait before re-enqueueing unacked
#: messages.  The max message delay is 7 days so this has to account for
#: that and give the workers some legroom.
DEFAULT_REQUEUE_DEADLINE = int(86400000 * 7.5)

#: The default interval with which to check for unacked messages.
DEFAULT_REQUEUE_INTERVAL = 3600000

#: The max amount of time messages can be delayed by in ms.
MAX_MESSAGE_DELAY = 86400000 * 7


class RedisBroker(Broker):
    """A broker than can be used with Redis.

    Examples:

      If you want to specify connection parameters individually:

      >>> RedisBroker(host="127.0.0.1", port=6379, db=0, password="hunter2")

      Alternatively, if you want to use a connection URL:

      >>> RedisBroker(url="redis://127.0.0.1:6379/0")

    See also:
      StrictRedis_ for a list of all the available connection parameters.

    Parameters:
      url(str): An optional connection URL.  If both a URL and
        connection parameters are provided, the URL is used.
      middleware(list[Middleware])
      namespace(str): The str with which to prefix all Redis keys.
      \**parameters(dict): Connection parameters are passed directly
        to :class:`redis.StrictRedis`.

    .. _StrictRedis: http://redis-py.readthedocs.io/en/latest/#redis.StrictRedis
    """

    def __init__(self, *, url=None, middleware=None, namespace="dramatiq", **parameters):  # noqa
        super().__init__(middleware=middleware)

        if url:
            parameters["connection_pool"] = redis.ConnectionPool.from_url(url)

        self.namespace = namespace
        self.dead_message_ttl = DEFAULT_DEAD_MESSAGE_TTL
        self.requeue_deadline = DEFAULT_REQUEUE_DEADLINE
        self.requeue_interval = DEFAULT_REQUEUE_INTERVAL
        self.queues = set()
        self.client = client = redis.StrictRedis(**parameters)
        self.scripts = {name: client.register_script(script) for name, script in _scripts.items()}
        self.watcher = _RedisWatcher(self, interval=self.requeue_interval)

    def close(self):
        """Close this broker.
        """
        self.watcher.stop()

    def consume(self, queue_name, prefetch=1, timeout=5000):
        """Create a new consumer for a queue.

        Parameters:
          queue_name(str): The queue to consume.
          prefetch(int): The number of messages to prefetch.
          timeout(int): The idle timeout in milliseconds.

        Returns:
          Consumer: A consumer that retrieves messages from Redis.
        """
        return _RedisConsumer(self, queue_name, prefetch, timeout)

    def declare_queue(self, queue_name):
        """Declare a queue.  Has no effect if a queue with the given
        name has already been declared.

        Parameters:
          queue_name(str): The name of the new queue.
        """
        if queue_name not in self.queues:
            self.emit_before("declare_queue", queue_name)
            self.queues.add(queue_name)
            self.emit_after("declare_queue", queue_name)

            delayed_name = dq_name(queue_name)
            self.delay_queues.add(delayed_name)
            self.emit_after("declare_delay_queue", delayed_name)

    def enqueue(self, message, *, delay=None):
        """Enqueue a message.

        Parameters:
          message(Message): The message to enqueue.
          delay(int): The minimum amount of time, in milliseconds, to
            delay the message by.  Must be less than 7 days.

        Raises:
          ValueError: If ``delay`` is longer than 7 days.
        """
        queue_name = message.queue_name

        # Each enqueued message must have a unique id in Redis so
        # using the Message's id isn't safe because messages may be
        # retried.
        message = message.copy(options={
            "redis_message_id": str(uuid4()),
        })

        if delay is not None:
            if delay > MAX_MESSAGE_DELAY:
                raise ValueError(
                    "Messages cannot be delayed for longer than 7 days. "
                    "Your message queue is not a Database."
                )

            queue_name = dq_name(queue_name)
            message_eta = current_millis() + delay
            message = message.copy(
                queue_name=queue_name,
                options={
                    "eta": message_eta,
                },
            )

        self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, queue_name)
        self.emit_before("enqueue", message, delay)
        self._enqueue(queue_name, message.options["redis_message_id"], message.encode())
        self.emit_after("enqueue", message, delay)
        return message

    def get_declared_queues(self):
        """Get all declared queues.

        Returns:
          set[str]: The names of all the queues declared so far on
          this Broker.
        """
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
        nack = self.scripts["nack"]
        timestamp = current_millis()
        xqueue_name = xq_name(queue_name)
        queue_name = self._add_namespace(queue_name)
        xqueue_name = self._add_namespace(xqueue_name)
        nack(args=[queue_name, xqueue_name, message_id, timestamp])

    def _requeue_messages(self, queue_name, message_ids):
        requeue = self.scripts["requeue_messages"]
        queue_name = self._add_namespace(queue_name)
        requeue(args=[queue_name], keys=message_ids)

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
                self.logger.debug("Running requeue...")
                self.broker._requeue()

                self.logger.debug("Running cleanup...")
                self.broker._cleanup()

            except Exception:
                self.logger.warning("Requeue failed.", exc_info=True)

            finally:
                time.sleep(self.interval / 1000)

    def stop(self):
        self.logger.debug("Stopping watcher...")
        self.running = False


class _RedisConsumer(Consumer):
    def __init__(self, broker, queue_name, prefetch, timeout):
        self.logger = get_logger(__name__, type(self))
        self.broker = broker
        self.queue_name = queue_name
        self.prefetch = prefetch
        self.timeout = timeout

        self.message_cache = []
        self.message_refc = 0
        self.misses = 0

    def ack(self, message):
        try:
            # The current queue might be different from message.queue_name
            # if the message has been delayed so we want to ack on the
            # current queue.
            self.broker._ack(self.queue_name, message.options["redis_message_id"])
        finally:
            self.message_refc -= 1

    def nack(self, message):
        try:
            # Same deal as above.
            self.broker._nack(self.queue_name, message.options["redis_message_id"])
        finally:
            self.message_refc -= 1

    def requeue(self, messages):
        message_ids = [message.options["redis_message_id"] for message in messages]
        if not message_ids:
            return

        self.logger.debug("Re-enqueueing %r on queue %r.", message_ids, self.queue_name)
        self.broker._requeue_messages(self.queue_name, message_ids)

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
                    return MessageProxy(message)
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
            raise ConnectionClosed(e) from None


_scripts = {}
_scripts_path = path.join(path.abspath(path.dirname(__file__)), "redis")
for filename in glob.glob(path.join(_scripts_path, "*.lua")):
    script_name, _ = path.splitext(path.basename(filename))
    with open(filename, "rb") as f:
        _scripts[script_name] = f.read()
