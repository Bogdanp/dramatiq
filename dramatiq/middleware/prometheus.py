# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018,2019 CLEARTYPE SRL <bogdan@cleartype.io>
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
import multiprocessing
import os
import shutil
import signal
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer

from ..common import current_millis, q_name
from ..logging import get_logger
from .middleware import Middleware

#: The HTTP host the exposition server should bind to.
HTTP_HOST = os.getenv("dramatiq_prom_host", "0.0.0.0")

#: The HTTP port the exposition server should listen on.
HTTP_PORT = int(os.getenv("dramatiq_prom_port", "9191"))


def _prom_db_path():
    """Determines Prometheus multiproc database path.

    Returns:
        tuple[str, bool]: (db_path, is_external)
            db_path     - path to DB directory
            is_external - True if DB path set externally via standard env variable
    """
    ext_path = os.getenv("DRAMATIQ_PROM_DB")
    if ext_path:
        return ext_path, True

    parent_proc = multiprocessing.parent_process()
    # un-possible: parent_proc is None if current process isn't a subprocess
    # this is supposed to be called only from subprocesses
    if not parent_proc:
        raise RuntimeError("No parent process found")
    db_path = f"{tempfile.gettempdir()}/dramatiq-prometheus-{parent_proc.pid}"
    return db_path, False


class Prometheus(Middleware):
    """A middleware that exports stats via Prometheus_.

    .. _Prometheus: https://prometheus.io
    """

    def __init__(self):
        self.logger = get_logger(__name__, type(self))
        self.delayed_messages = set()
        self.message_start_times = {}

    @property
    def forks(self):
        return [_run_exposition_server, _cleanup_on_shutdown]

    def after_process_boot(self, broker):
        # setting up Prometheus multi-process environment
        db_path, _ = _prom_db_path()
        os.makedirs(db_path, exist_ok=True)
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = db_path
        self.logger.debug("prometheus DB path: %s", db_path)

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
        self.total_retried_messages = prom.Counter(
            "dramatiq_message_retries_total",
            "The total number of retried messages.",
            ["queue_name", "actor_name"],
            registry=registry,
        )
        self.total_rejected_messages = prom.Counter(
            "dramatiq_message_rejects_total",
            "The total number of dead-lettered messages.",
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
        self.inprogress_delayed_messages = prom.Gauge(
            "dramatiq_delayed_messages_inprogress",
            "The number of delayed messages in memory.",
            ["queue_name", "actor_name"],
            registry=registry,
            multiprocess_mode="livesum",
        )
        self.message_durations = prom.Histogram(
            "dramatiq_message_duration_milliseconds",
            "The time spent processing messages.",
            ["queue_name", "actor_name"],
            buckets=(5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000,
                     7500, 10000, 30000, 60000, 600000, 900000, float("inf")),
            registry=registry,
        )

    @staticmethod
    def _standard_labels(message):
        # use canonical queue names in metrics
        return q_name(message.queue_name), message.actor_name

    def after_worker_shutdown(self, broker, worker):
        from prometheus_client import multiprocess

        self.logger.debug("Marking process dead...")
        multiprocess.mark_process_dead(os.getpid())

    def after_nack(self, broker, message):
        labels = self._standard_labels(message)
        self.total_rejected_messages.labels(*labels).inc()

    def after_enqueue(self, broker, message, delay):
        if "retries" in message.options:
            labels = self._standard_labels(message)
            self.total_retried_messages.labels(*labels).inc()

    def before_delay_message(self, broker, message):
        labels = self._standard_labels(message)
        self.delayed_messages.add(message.message_id)
        self.inprogress_delayed_messages.labels(*labels).inc()

    def before_process_message(self, broker, message):
        labels = self._standard_labels(message)
        if message.message_id in self.delayed_messages:
            self.delayed_messages.remove(message.message_id)
            self.inprogress_delayed_messages.labels(*labels).dec()

        self.inprogress_messages.labels(*labels).inc()
        self.message_start_times[message.message_id] = current_millis()

    def after_process_message(self, broker, message, *, result=None, exception=None):
        labels = self._standard_labels(message)
        message_start_time = self.message_start_times.pop(message.message_id, current_millis())
        message_duration = current_millis() - message_start_time
        self.message_durations.labels(*labels).observe(message_duration)
        self.inprogress_messages.labels(*labels).dec()
        self.total_messages.labels(*labels).inc()
        if exception is not None:
            self.total_errored_messages.labels(*labels).inc()

    after_skip_message = after_process_message


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # These imports must happen at runtime.  See above.
        import prometheus_client as prom
        from prometheus_client import multiprocess as prom_mp

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


def _run_exposition_server():
    logger = get_logger(__name__, "_run_exposition_server")
    logger.debug("Starting exposition server...")

    def sig_handler(_signum, _frame):
        logger.debug("Caught SIGTERM")
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, sig_handler)

    db_path, _ = _prom_db_path()
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = db_path

    try:
        address = (HTTP_HOST, HTTP_PORT)
        httpd = HTTPServer(address, _MetricsHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.debug("Stopping exposition server...")
        httpd.shutdown()

    return 0


def _cleanup_on_shutdown():
    """Main process fork. Waits for SIGTERM (graceful shutdown) and cleans up Prometheus database
    directory, if using unique path based on parent PID.
    """
    db_path, is_external = _prom_db_path()
    logger = get_logger(__name__, "_cleanup_on_shutdown")
    logger.debug("Starting cleanup waiter; using DB path: %s", db_path)

    if not is_external:
        signal.sigwaitinfo([signal.SIGTERM])
        logger.debug("Caught SIGTERM, cleaning up DB directory: %s", db_path)
        try:
            shutil.rmtree(db_path)
        except OSError:
            logger.exception("error during DB directory cleanup")
    else:
        logger.debug("Cleanup waiter skipped, DB path is overridden via ENV var")

    return 0
