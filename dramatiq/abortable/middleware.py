import threading
import time
import warnings
from threading import Thread

from ..logging import get_logger
from ..middleware import Middleware, SkipMessage
from ..middleware.threading import Interrupt, current_platform, raise_thread_exception, supported_platforms


class Abort(Interrupt):
    """Exception used to interrupt worker threads when their worker
    processes have been signaled to abort.
    """


class Abortable(Middleware):
    """Middleware that interrupts actors whose job has been signaled for
    termination.
    Currently, this is only available on CPython.

    Note:
      This works by setting an async exception in the worker thread
      that runs the actor.  This means that the exception will only get
      called the next time that thread acquires the GIL.  Concretely,
      this means that this middleware can't cancel system calls.

    Parameters:
      abortable(bool): When true, the actor will be interrupted
        if the task was aborted.
    """
    def __init__(self, *, backend, abortable: bool = True):
        self.logger = get_logger(__name__, type(self))
        self.abortable = abortable
        self.backend = backend
        self.wait_timeout = 1000
        self.abort_ttl = 90000
        self.abortables = {}
        # This lock avoid race between the monitor and a task cleaning up.
        self.lock = threading.Lock()

    @property
    def actor_options(self):
        return {"abortable"}

    def is_abortable(self, actor, message):
        abortable = message.options.get("abortable")
        if abortable is None:
            abortable = actor.options.get("abortable")
        if abortable is None:
            abortable = self.abortable
        return bool(abortable)

    def after_process_boot(self, broker):
        if current_platform in supported_platforms:
            thread = Thread(target=self._watcher, daemon=True)
            thread.start()
        else:  # pragma: no cover
            msg = "Abortable cannot kill threads on your current platform (%r)."
            warnings.warn(msg % current_platform, category=RuntimeWarning, stacklevel=2)

    def before_process_message(self, broker, message):
        actor = broker.get_actor(message.actor_name)
        if not self.is_abortable(actor, message):
            return

        if self.backend.poll(self.id_to_key(message.message_id)):
            raise SkipMessage()

        self.abortables[message.message_id] = threading.get_ident()

    def after_process_message(self, broker, message, *, result=None, exception=None):
        with self.lock:
            self.abortables.pop(message.message_id, None)

    after_skip_message = after_process_message

    def abort(self, message_id):
        self.backend.notify(self.id_to_key(message_id), ttl=self.abort_ttl)

    def _handle(self):
        message_ids = self.abortables.keys()
        if not message_ids:
            time.sleep(self.wait_timeout / 1000)
            return

        abort_keys = [self.id_to_key(id_) for id_ in message_ids]
        key = self.backend.wait_many(abort_keys, self.wait_timeout)
        if not key:
            return

        # Trim "abort:".
        message_id = self.key_to_id(key)
        with self.lock:
            thread_id = self.abortables.pop(message_id, None)
            if thread_id is None:
                return

            self.logger.info("Aborting task. Raising exception in worker thread %r.", thread_id)
            raise_thread_exception(thread_id, Abort)

    def _watcher(self):
        while True:
            try:
                self._handle()
            except Exception:  # pragma: no cover
                self.logger.exception("Unhandled error while running the time limit handler.")

    @staticmethod
    def id_to_key(message_id):
        return ("abort:" + message_id).encode()

    @staticmethod
    def key_to_id(key):
        return key.decode()[6:]
