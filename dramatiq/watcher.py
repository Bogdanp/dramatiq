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


def setup_file_watcher(path, use_polling=False, include_patterns=None, exclude_patterns=None):
    """Sets up a background thread that watches for source changes and
    automatically sends SIGHUP to the current process whenever a file
    changes.
    """
    if use_polling:
        observer_class = watchdog.observers.polling.PollingObserver
    else:
        observer_class = EVENTED_OBSERVER

    if include_patterns is None:
        include_patterns = ["*.py"]

    file_event_handler = _SourceChangesHandler(
        patterns=include_patterns, ignore_patterns=exclude_patterns
    )
    file_watcher = observer_class()
    file_watcher.schedule(file_event_handler, path, recursive=True)
    file_watcher.start()
    return file_watcher


class _SourceChangesHandler(watchdog.events.PatternMatchingEventHandler):  # pragma: no cover
    """Handles source code change events by sending a HUP signal to
    the current process.
    """

    def on_any_event(self, event: watchdog.events.FileSystemEvent):
        # watchdog >= 2.3 emits an extra event when a file is opened that will cause unnecessary
        # restarts.  This affects any usage of watchdog where a custom event handler is used, including
        # this _SourceChangesHandler.
        #
        # For more context, see:
        #   https://github.com/gorakhargosh/watchdog/issues/949
        #   https://github.com/pallets/werkzeug/pull/2604/files
        if event.event_type == "opened":
            return

        logger = logging.getLogger("SourceChangesHandler")
        logger.info("Detected changes to %r.", event.src_path)
        os.kill(os.getpid(), signal.SIGHUP)
