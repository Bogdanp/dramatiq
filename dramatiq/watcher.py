import logging
import os
import signal

import watchdog.events
import watchdog.observers.polling

try:
    import watchdog_gevent

    EVENTED_OBSERVER = watchdog_gevent.Observer
except ImportError:
    EVENTED_OBSERVER = watchdog.observers.Observer


def setup_file_watcher(path, use_polling=False):
    """Sets up a background thread that watches for source changes and
    automatically sends SIGHUP to the current process whenever a file
    changes.
    """
    if use_polling:
        observer_class = watchdog.observers.polling.PollingObserver
    else:
        observer_class = EVENTED_OBSERVER

    file_event_handler = _SourceChangesHandler(patterns=["*.py"])
    file_watcher = observer_class()
    file_watcher.schedule(file_event_handler, path, recursive=True)
    file_watcher.start()
    return file_watcher


class _SourceChangesHandler(watchdog.events.PatternMatchingEventHandler):  # pragma: no cover
    """Handles source code change events by sending a HUP signal to
    the current process.
    """

    def on_any_event(self, event):
        logger = logging.getLogger("SourceChangesHandler")
        logger.info("Detected changes to %r.", event.src_path)
        os.kill(os.getpid(), signal.SIGHUP)
