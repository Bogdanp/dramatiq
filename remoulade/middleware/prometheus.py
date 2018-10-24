# This file is a part of Remoulade.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Remoulade is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Remoulade is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import fcntl
import os
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from ..common import current_millis
from ..logging import get_logger
from .middleware import Middleware

#: The path to the file to use to race Exposition servers against one another.
LOCK_PATH = os.getenv("remoulade_prom_lock", "/tmp/remoulade-prometheus.lock")

#: The path to store the prometheus database files.  This path is
#: cleared before every run.
DB_PATH = os.getenv("remoulade_prom_db", "/tmp/remoulade-prometheus")

#: The default HTTP host the exposition server should bind to.
DEFAULT_HTTP_HOST = os.getenv("remoulade_prom_host", "127.0.0.1")

#: The default HTTP port the exposition server should listen on.
DEFAULT_HTTP_PORT = int(os.getenv("remoulade_prom_port", "9191"))


class Prometheus(Middleware):
    """A middleware that exports stats via Prometheus_.

    Parameters:
      http_host(str): The host to bind the Prometheus exposition
        server on.  This parameter can also be configured via the
        ``remoulade_prom_host`` environment variable.
      http_port(int): The port on which the server should listen.
        This parameter can also be configured via the
        ``remoulade_prom_port`` environment variable.

    .. _Prometheus: https://prometheus.io
    """

    def __init__(self, *, http_host=DEFAULT_HTTP_HOST, http_port=DEFAULT_HTTP_PORT):
        self.logger = get_logger(__name__, type(self))
        self.http_host = http_host
        self.http_port = http_port
        self.delayed_messages = set()
        self.message_start_times = {}

    def after_process_boot(self, broker):
        os.environ["prometheus_multiproc_dir"] = DB_PATH

        # This import MUST happen at runtime, after process boot and
        # after the env variable has been set up.
        import prometheus_client as prom

        self.logger.debug("Setting up metrics...")
        registry = prom.CollectorRegistry()
        self.total_messages = prom.Counter(
            "remoulade_messages_total",
            "The total number of messages processed.",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.total_errored_messages = prom.Counter(
            "remoulade_message_errors_total",
            "The total number of errored messages.",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.total_retried_messages = prom.Counter(
            "remoulade_message_retries_total",
            "The total number of retried messages.",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.total_rejected_messages = prom.Counter(
            "remoulade_message_rejects_total",
            "The total number of dead-lettered messages.",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.inprogress_messages = prom.Gauge(
            "remoulade_messages_inprogress",
            "The number of messages in progress.",
            ["queue_name", "actor_name"],
            registry=registry,
            multiprocess_mode="livesum",
        )
        self.inprogress_delayed_messages = prom.Gauge(
            "remoulade_delayed_messages_inprogress",
            "The number of delayed messages in memory.",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.message_durations = prom.Histogram(
            "remoulade_message_duration_milliseconds",
            "The time spent processing messages.",
            ["queue_name", "actor_name"],
            buckets=(5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000,
                     7500, 10000, 30000, 60000, 600000, 900000, float("inf")),
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
        from prometheus_client import multiprocess

        self.logger.debug("Marking process dead...")
        multiprocess.mark_process_dead(os.getpid(), DB_PATH)

        self.logger.debug("Shutting down exposition server...")
        self.server.stop()

    def after_nack(self, broker, message):
        labels = (message.queue_name, message.actor_name)
        self.total_rejected_messages.labels(*labels).inc()

    def after_enqueue(self, broker, message, delay):
        if "retries" in message.options:
            labels = (message.queue_name, message.actor_name)
            self.total_retried_messages.labels(*labels).inc()

    def before_delay_message(self, broker, message):
        labels = (message.queue_name, message.actor_name)
        self.delayed_messages.add(message.message_id)
        self.inprogress_delayed_messages.labels(*labels).inc()

    def before_process_message(self, broker, message):
        labels = (message.queue_name, message.actor_name)
        if message.message_id in self.delayed_messages:
            self.delayed_messages.remove(message.message_id)
            self.inprogress_delayed_messages.labels(*labels).dec()

        self.inprogress_messages.labels(*labels).inc()
        self.message_start_times[message.message_id] = current_millis()

    def after_process_message(self, broker, message, *, result=None, exception=None):
        labels = (message.queue_name, message.actor_name)
        message_start_time = self.message_start_times.pop(message.message_id, current_millis())
        message_duration = current_millis() - message_start_time
        self.message_durations.labels(*labels).observe(message_duration)
        self.inprogress_messages.labels(*labels).dec()
        self.total_messages.labels(*labels).inc()
        if exception is not None:
            self.total_errored_messages.labels(*labels).inc()

    after_skip_message = after_process_message


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
            if not os.path.exists(DB_PATH):
                os.makedirs(DB_PATH)

            try:
                self.httpd = HTTPServer(self.address, metrics_handler)
                self.httpd.serve_forever()
            except OSError:
                self.logger.warning("Failed to bind exposition server.", exc_info=True)

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.join()


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
