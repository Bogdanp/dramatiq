from __future__ import annotations

import time
import urllib.request as request
from threading import Thread

import dramatiq
from dramatiq import Message
from dramatiq.middleware.prometheus import Prometheus, _run_exposition_server


def get_delayed_gauge_values(prometheus, actor_name):
    [metric] = prometheus.inprogress_delayed_messages.collect()
    return {
        sample.labels["queue_name"]: sample.value
        for sample in metric.samples
        if sample.labels["actor_name"] == actor_name
    }


def test_prometheus_middleware_exposes_metrics():
    # Given an instance of the exposition server
    thread = Thread(target=_run_exposition_server, daemon=True)
    thread.start()

    # When I give it time to boot up
    time.sleep(1)

    # And I request metrics via HTTP
    with request.urlopen("http://127.0.0.1:9191") as resp:
        # Then the response should be successful
        assert resp.getcode() == 200


def test_prometheus_middleware_tracks_delayed_messages_until_they_are_enqueued(stub_broker, stub_worker):
    # Given a broker with the prometheus middleware
    prometheus = Prometheus()
    stub_broker.add_middleware(prometheus)
    prometheus.after_process_boot(stub_broker)

    # And an actor
    @dramatiq.actor
    def do_delayed_work():
        pass

    # When I send that actor a delayed message
    do_delayed_work.send_with_options(delay=100)

    # wait for it to be processed
    stub_broker.join(do_delayed_work.queue_name)
    stub_worker.join()

    # Then the delayed messages gauge should be back to 0
    assert get_delayed_gauge_values(prometheus, "do_delayed_work") == {"default": 0}

    # And no delayed messages should be tracked
    assert prometheus.delayed_messages == set()


def test_prometheus_middleware_decrements_delayed_messages_once_on_ack(stub_broker):
    # Given a broker with the prometheus middleware
    prometheus = Prometheus()
    stub_broker.add_middleware(prometheus)
    prometheus.after_process_boot(stub_broker)

    # And a message on a delay queue
    message = Message(
        queue_name="default.DQ",
        actor_name="do_acked_work",
        args=(),
        kwargs={},
        options={},
    )

    # When that message is delayed
    prometheus.before_delay_message(stub_broker, message)

    # And then acked twice, without being processed by this process
    prometheus.after_ack(stub_broker, message)
    prometheus.after_ack(stub_broker, message)

    # Then the delayed messages gauge should be back to 0
    assert get_delayed_gauge_values(prometheus, "do_acked_work") == {"default": 0}

    # And no delayed messages should be tracked
    assert prometheus.delayed_messages == set()


def test_prometheus_middleware_counts_redelivered_delayed_messages_once(stub_broker):
    # Given a broker with the prometheus middleware
    prometheus = Prometheus()
    stub_broker.add_middleware(prometheus)
    prometheus.after_process_boot(stub_broker)

    # And a message on a delay queue
    message = Message(
        queue_name="default.DQ",
        actor_name="do_redelivered_work",
        args=(),
        kwargs={},
        options={},
    )

    # When that message is delayed twice, as happens when it's redelivered
    prometheus.before_delay_message(stub_broker, message)
    prometheus.before_delay_message(stub_broker, message)

    # And then acked once
    prometheus.after_ack(stub_broker, message)

    # Then the delayed messages gauge should be back to 0
    assert get_delayed_gauge_values(prometheus, "do_redelivered_work") == {"default": 0}

    # And no delayed messages should be tracked
    assert prometheus.delayed_messages == set()
