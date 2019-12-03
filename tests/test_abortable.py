import time

import pytest

import dramatiq
from dramatiq.middleware import threading
from dramatiq.abortable import Abort, Abortable

not_supported = threading.current_platform not in threading.supported_platforms


@pytest.mark.skipif(not_supported, reason="Threading not supported on this platform.")
def test_abort_notifications_are_received(stub_broker, stub_worker, event_backend):
    # Given that I have a database
    aborts, successes = [], []

    abortable = Abortable(backend=event_backend)
    stub_broker.add_middleware(abortable)

    # And an actor that handles shutdown interrupts
    @dramatiq.actor(abortable=True, max_retries=0)
    def do_work():
        try:
            for _ in range(10):
                time.sleep(.1)
        except Abort:
            aborts.append(1)
            raise
        successes.append(1)

    stub_broker.emit_after("process_boot")

    # If I send it a message
    message = do_work.send()

    # Then wait and signal the task to terminate
    time.sleep(.1)
    message.abort()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I expect it to shutdown
    assert sum(aborts) == 1
    assert sum(successes) == 0
