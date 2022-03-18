# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import glob
import random
import time
import warnings
from os import path
from threading import Lock
from uuid import uuid4

import redis

from ..broker import Broker, Consumer, MessageProxy
from ..common import compute_backoff, current_millis, dq_name, getenv_int
from ..errors import ConnectionClosed, QueueJoinTimeout
from ..logging import get_logger
from ..message import Message

MAINTENANCE_SCALE = 1000000
MAINTENANCE_COMMAND_BLACKLIST = {"ack", "nack"}

#: How many commands out of a million should trigger queue
#: maintenance.
DEFAULT_MAINTENANCE_CHANCE = 1000

#: The amount of time in milliseconds that dead-lettered messages are
#: kept in Redis for.
DEFAULT_DEAD_MESSAGE_TTL = 86400000 * 7

#: The amount of time in milliseconds that has to pass without a
#: heartbeat for a worker to be considered offline.
DEFAULT_HEARTBEAT_TIMEOUT = 60000

#: A hint for the max lua stack size. The broker discovers this value
#: the first time it's run, but it may be overwritten using this var.
DEFAULT_LUA_MAX_STACK = getenv_int("dramatiq_lua_max_stack")


class RedisBroker(Broker):
    """A broker than can be used with Redis.

    Examples:

      If you want to specify connection parameters individually:

      >>> RedisBroker(host="127.0.0.1", port=6379, db=0, password="hunter2")

      Alternatively, if you want to use a connection URL:

      >>> RedisBroker(url="redis://127.0.0.1:6379/0")

    See also:
      Redis_ for a list of all the available connection parameters.

    Parameters:
      url(str): An optional connection URL.  If both a URL and
        connection parameters are provided, the URL is used.
      middleware(list[Middleware])
      maintenance_chance(int): How many commands out of a million
        should trigger queue maintenance.
      namespace(str): The str with which to prefix all Redis keys.
      heartbeat_timeout(int): The amount of time (in ms) that has to
        pass without a heartbeat for a broker process to be considered
        offline.
      dead_message_ttl(int): The amount of time (in ms) that
        dead-lettered messages are kept in Redis for.
      requeue_deadline(int): Deprecated.  Does nothing.
      requeue_interval(int): Deprecated.  Does nothing.
      client(redis.StrictRedis): A redis client to use.
      **parameters: Connection parameters are passed directly
        to :class:`redis.Redis`.

    .. _Redis: http://redis-py.readthedocs.io/en/latest/#redis.Redis
    """

    def __init__(
            self, *,
            url=None, middleware=None, namespace="dramatiq",
            maintenance_chance=DEFAULT_MAINTENANCE_CHANCE,
            heartbeat_timeout=DEFAULT_HEARTBEAT_TIMEOUT,
            dead_message_ttl=DEFAULT_DEAD_MESSAGE_TTL,
            requeue_deadline=None,
            requeue_interval=None,
            client=None,
            **parameters
    ):
        super().__init__(middleware=middleware)

        if url:
            parameters["connection_pool"] = redis.ConnectionPool.from_url(url)

        if requeue_deadline or requeue_interval:
            message = "requeue_{deadline,interval} have been deprecated and no longer do anything"
            warnings.warn(message, DeprecationWarning, stacklevel=2)

        self.broker_id = str(uuid4())
        self.namespace = namespace
        self.maintenance_chance = maintenance_chance
        self.heartbeat_timeout = heartbeat_timeout
        self.dead_message_ttl = dead_message_ttl
        self.queues = set()
        # TODO: Replace usages of StrictRedis (redis-py 2.x) with Redis in Dramatiq 2.0.
        self.client = client or redis.StrictRedis(**parameters)
        self.scripts = {name: self.client.register_script(script) for name, script in _scripts.items()}

    @property
    def consumer_class(self):
        return _RedisConsumer

    def consume(self, queue_name, prefetch=1, timeout=5000):
        """Create a new consumer for a queue.

        Parameters:
          queue_name(str): The queue to consume.
          prefetch(int): The number of messages to prefetch.
          timeout(int): The idle timeout in milliseconds.

        Returns:
          Consumer: A consumer that retrieves messages from Redis.
        """
        return self.consumer_class(self, queue_name, prefetch, timeout)

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
        self.do_enqueue(queue_name, message.options["redis_message_id"], message.encode())
        self.emit_after("enqueue", message, delay)
        return message

    def get_declared_queues(self):
        """Get all declared queues.

        Returns:
          set[str]: The names of all the queues declared so far on
          this Broker.
        """
        return self.queues.copy()

    def flush(self, queue_name):
        """Drop all the messages from a queue.

        Parameters:
          queue_name(str): The queue to flush.
        """
        for name in (queue_name, dq_name(queue_name)):
            self.do_purge(name)

    def flush_all(self):
        """Drop all messages from all declared queues.
        """
        for queue_name in self.queues:
            self.flush(queue_name)

    def join(self, queue_name, *, interval=100, timeout=None):
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests to
        wait for all the messages in a queue to be processed.

        Raises:
          QueueJoinTimeout: When the timeout elapses.

        Parameters:
          queue_name(str): The queue to wait on.
          interval(Optional[int]): The interval, in milliseconds, at
            which to check the queues.
          timeout(Optional[int]): The max amount of time, in
            milliseconds, to wait on this queue.
        """
        deadline = timeout and time.monotonic() + timeout / 1000
        while True:
            if deadline and time.monotonic() >= deadline:
                raise QueueJoinTimeout(queue_name)

            size = self.do_qsize(queue_name)

            if size == 0:
                return

            time.sleep(interval / 1000)

    def _should_do_maintenance(self, command):
        return int(
            command not in MAINTENANCE_COMMAND_BLACKLIST and
            random.randint(1, MAINTENANCE_SCALE) <= self.maintenance_chance
        )

    _max_unpack_size_val = None
    _max_unpack_size_mut = Lock()

    def _max_unpack_size(self):
        cls = type(self)
        if cls._max_unpack_size_val is None:
            with cls._max_unpack_size_mut:
                if cls._max_unpack_size_val is None:
                    cls._max_unpack_size_val = DEFAULT_LUA_MAX_STACK or self.scripts["maxstack"]()
                    # We only want to use half of the max LUA stack to unpack values to avoid having
                    # problems with multiple workers + great number of messages
                    # See https://github.com/Bogdanp/dramatiq/issues/433
                    cls._max_unpack_size_val = cls._max_unpack_size_val // 2
        return cls._max_unpack_size_val

    def _dispatch(self, command):
        # Micro-optimization: by hoisting these up here we avoid
        # allocating the list on every call.
        dispatch = self.scripts["dispatch"]
        keys = [self.namespace]

        def do_dispatch(queue_name, *args):
            timestamp = current_millis()
            args = [
                command,
                timestamp,
                queue_name,
                self.broker_id,
                self.heartbeat_timeout,
                self.dead_message_ttl,
                self._should_do_maintenance(command),
                self._max_unpack_size(),
                *args,
            ]
            return dispatch(args=args, keys=keys)
        return do_dispatch

    def __getattr__(self, name):
        if not name.startswith("do_"):
            raise AttributeError("attribute %s does not exist" % name)

        command = name[len("do_"):]
        return self._dispatch(command)


class _RedisConsumer(Consumer):
    def __init__(self, broker, queue_name, prefetch, timeout):
        self.logger = get_logger(__name__, type(self))
        self.broker = broker
        self.queue_name = queue_name
        self.prefetch = prefetch
        self.timeout = timeout

        self.message_cache = []
        self.queued_message_ids = set()
        self.misses = 0

    @property
    def outstanding_message_count(self):
        return len(self.queued_message_ids) + len(self.message_cache)

    def ack(self, message):
        try:
            # The current queue might be different from message.queue_name
            # if the message has been delayed so we want to ack on the
            # current queue.
            self.broker.do_ack(self.queue_name, message.options["redis_message_id"])
        except redis.ConnectionError as e:
            raise ConnectionClosed(e) from None
        finally:
            self.queued_message_ids.discard(message.message_id)

    def nack(self, message):
        try:
            # Same deal as above.
            self.broker.do_nack(self.queue_name, message.options["redis_message_id"])
        except redis.ConnectionError as e:
            raise ConnectionClosed(e) from None
        finally:
            self.queued_message_ids.discard(message.message_id)

    def requeue(self, messages):
        message_ids = [message.options["redis_message_id"] for message in messages]
        if not message_ids:
            return

        self.logger.debug("Re-enqueueing %r on queue %r.", message_ids, self.queue_name)
        self.broker.do_requeue(self.queue_name, *message_ids)

    def __next__(self):
        try:
            while True:
                try:
                    # This is a micro-optimization so we try the fast
                    # path first.  We assume there are messages in the
                    # cache and if there aren't, we go down the slow
                    # path of doing network IO.
                    data = self.message_cache.pop(0)
                    if data is None:
                        self.logger.warning(
                            "Found 'None' message in message cache for queue %r. "
                            "This may be a bug in dramatiq (related to #266), please report it.",
                            self.queue_name,
                        )
                        continue
                    self.misses = 0

                    message = Message.decode(data)
                    self.queued_message_ids.add(message.message_id)
                    return MessageProxy(message)
                except IndexError:
                    # If there are fewer messages currently being
                    # processed than we're allowed to prefetch,
                    # prefetch up to that number of messages.
                    messages = []
                    if self.outstanding_message_count < self.prefetch:
                        self.message_cache = messages = self.broker.do_fetch(
                            self.queue_name,
                            self.prefetch - self.outstanding_message_count,
                        )

                    # Because we didn't get any messages, we should
                    # progressively long poll up to the idle timeout.
                    if not messages:
                        self.misses, backoff_ms = compute_backoff(self.misses, max_backoff=self.timeout)
                        time.sleep(backoff_ms / 1000)
                        return None
        except redis.ConnectionError as e:
            raise ConnectionClosed(e) from None


_scripts = {}
_scripts_path = path.join(path.abspath(path.dirname(__file__)), "redis")
for filename in glob.glob(path.join(_scripts_path, "*.lua")):
    script_name, _ = path.splitext(path.basename(filename))
    with open(filename, "rb") as f:
        _scripts[script_name] = f.read()
