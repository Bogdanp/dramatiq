import fcntl
import glob
import os

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread

from ..common import current_millis
from ..logging import get_logger
from .middleware import Middleware

#: The path to the file to use to race Exposition servers against one another.
LOCK_PATH = os.getenv("dramatiq_prom_lock", "/tmp/dramatiq-prometheus.lock")

#: The path to store the prometheus database files.  This path is
#: cleared before every run.
DB_PATH = os.getenv("dramatiq_prom_db", "/tmp/dramatiq-prometheus")


class Prometheus(Middleware):
    """A middleware that exports stats via Prometheus_.

    Parameters:
      http_host(str): The host to bind the Prometheus exposition server on.
      http_port(int): The port on which the server should listen.

    .. _Prometheus: https://prometheus.io
    """

    def __init__(self, *, http_host="localhost", http_port=9191):
        self.logger = get_logger(__name__, type(self))
        self.http_host = http_host
        self.http_port = http_port
        self.durations_by_message = {}

    def after_process_boot(self, broker):
        os.environ["prometheus_multiproc_dir"] = DB_PATH

        # This import MUST happen at runtime, after process boot and
        # after the env variable has been set up.
        import prometheus_client as prom

        self.logger.debug("Setting up metrics...")
        registry = prom.CollectorRegistry()
        self.total_messages = prom.Counter(
            "dramatiq_messages_total",
            "The total number of messages processed.",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.total_errored_messages = prom.Counter(
            "dramatiq_message_errors_total",
            "The total number of errored messages.",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.total_rejected_messages = prom.Counter(
            "dramatiq_message_rejects_total",
            "The total number of rejected messages (moved to the DLQ).",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.inprogress_messages = prom.Gauge(
            "dramatiq_messages_inprogress",
            "The number of messages in progress.",
            ["queue_name", "actor_name"],
            registry=registry,
            multiprocess_mode="livesum",
        )
        self.message_durations = prom.Histogram(
            "dramatiq_message_duration_milliseconds",
            "The time spent processing messages.",
            ["queue_name", "actor_name"],
            registry=registry,
        )

        self.logger.debug("Starting exposition server...")
        self.server = _ExpositionServer(
            http_host=self.http_host,
            http_port=self.http_port,
            lockfile=LOCK_PATH,
        )
        self.server.start()

    def after_worker_shutdown(self, broker, worker):
        self.logger.debug("Shutting down exposition server...")
        self.server.stop()

    def after_reject(self, broker, message):
        self.total_rejected_messages.labels(message.queue_name, message.actor_name).inc()

    def before_process_message(self, broker, message):
        self.inprogress_messages.labels(message.queue_name, message.actor_name).inc()
        self.durations_by_message[message.message_id] = current_millis()

    def after_process_message(self, broker, message, *, result=None, exception=None):
        labels = (message.queue_name, message.actor_name)
        message_duration = max(0, current_millis() - self.durations_by_message.pop(message.message_id))
        self.message_durations.labels(*labels).observe(message_duration)
        self.inprogress_messages.labels(*labels).dec()
        self.total_messages.labels(*labels).inc()
        if exception is not None:
            self.total_errored_messages.labels(*labels).inc()


class _ExpositionServer(Thread):
    """Exposition servers race against a POSIX lock in order to bind
    an HTTP server that can expose Prometheus metrics in the
    background.
    """

    def __init__(self, *, http_host, http_port, lockfile):
        super().__init__(daemon=True)

        self.logger = get_logger(__name__, type(self))
        self.address = (http_host, http_port)
        self.httpd = None
        self.lockfile = lockfile

    def run(self):
        with flock(self.lockfile) as acquired:
            if not acquired:
                self.logger.debug("Failed to acquire lock file.")
                return

            self.logger.debug("Lock file acquired. Running exposition server.")
            self.cleanup_db_path()

            try:
                self.httpd = _ThreadedHTTPd(self.address, metrics_handler)
                self.httpd.serve_forever()
            except OSError:
                self.logger.warning("Failed to bind exposition server.", exc_info=True)

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.join()

    def cleanup_db_path(self):
        if not os.path.exists(DB_PATH):
            os.makedirs(DB_PATH)

        for dbfile in glob.glob(os.path.join(DB_PATH, "*.db")):
            try:
                os.unlink(dbfile)
            except OSError:
                pass


class _ThreadedHTTPd(ThreadingMixIn, HTTPServer):
    """A simple threaded HTTP server.
    """


class metrics_handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # These imports must happen at runtime.  See above.
        import prometheus_client as prom
        import prometheus_client.multiprocess as prom_mp

        registry = prom.CollectorRegistry()
        prom_mp.MultiProcessCollector(registry)
        output = prom.generate_latest(registry)
        self.send_response(200)
        self.send_header("content-type", prom.CONTENT_TYPE_LATEST)
        self.end_headers()
        self.wfile.write(output)

    def log_message(self, fmt, *args):
        logger = get_logger(__name__, type(self))
        logger.debug(fmt, *args)


@contextmanager
def flock(path):
    """Attempt to acquire a POSIX file lock.
    """
    with open(path, "w+") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
            yield acquired

        except OSError:
            acquired = False
            yield acquired

        finally:
            if acquired:
                fcntl.flock(lf, fcntl.LOCK_UN)
