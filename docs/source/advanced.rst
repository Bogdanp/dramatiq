.. include:: global.rst

Advanced Topics
===============

Prometheus Metrics
------------------

Prometheus metrics are automatically exported by workers whenever you
boot them using the command line utility.  By default, the exposition
server listens on http://localhost:9191 so you can point Prometheus at
that or you can specify what host and port it should bind on by
setting the ``dramatiq_prom_host`` and ``dramatiq_prom_port``
environment variables.

The following metrics are exported:

``dramatiq_messages_total``
  A *counter* for the total number of messages processed.

``dramatiq_message_errors_total``
  A *counter* for the total number of errored messages.

``dramatiq_message_retries_total``
  A *counter* for the total number of retried messages.

``dramatiq_message_rejects_total``
  A *counter* for the total number of dead-lettered messages.

``dramatiq_messages_inprogress``
  A *gauge* for the number of messages currently being processed.

``dramatiq_delayed_messages_inprogress``
  A *gauge* for the number of delayed messages currently in memory.

``dramatiq_message_duration_milliseconds``
  A *histogram* for the time spent processing messages.

All metrics define labels for ``queue_name`` and ``actor_name``.


Using gevent
------------

Dramatiq comes with a CLI utility called ``dramatiq-gevent`` that can
run workers under gevent_.  The following invocation would run 8
worker processes with 250 greenlets per process for a total of 2k
lightweight worker threads::

  $ dramatiq-gevent my_app -p 8 -t 250

If your tasks spend most of their time doing network IO and don't
depend on C extensions to execute those network calls then using
gevent could provide a significant performance improvement.

I suggest at least experimenting with it to see if it fits your use
case.
