.. include:: global.rst

Advanced Topics
===============

Signals
-------

The main Dramatiq process responds to several signals::

  $ kill -TERM [master-process-pid]

``INT`` and ``TERM``
^^^^^^^^^^^^^^^^^^^^

Sending an ``INT`` or ``TERM`` signal to the main process triggers
graceful shutdown.  Consumer threads will stop receiving new work and
worker threads will finish processing the work they have in flight
before shutting down.  Any tasks still in worker memory at this point
are re-queued on the broker.

If you send a second ``TERM`` signal then the worker processes will be
killed immediately.

``HUP``
^^^^^^^

Sending ``HUP`` to the main process triggers a graceful shutdown
followed by a reload of the workers.  This is useful if you want to
reload code without completely restarting the main process.


Enqueueing Messages from Other Languages
----------------------------------------

You can enqueue Dramatiq messages using any language that has bindings
to one of its brokers.  All you have to do is push a JSON-encoded
dictionary containing the following fields to your queue:

.. code-block:: javascript

   {
     "queue_name": "default",     // The name of the queue the message is being pushed on
     "actor_name": "add",         // The name of the actor that should handle this message
     "args": [1, 2],              // A list of positional arguments that are passed to the actor
     "kwargs": {},                // A dictionary of keyword arguments that are passed to the actor
     "options": {},               // Arbitrary options that are used by middleware. Leave this empty
     "message_id": "unique-id",   // A UUID4 value representing the message's unique id in the system
     "message_timestamp": 0,      // The UNIX timestamp in milliseconds representing when the message was first enqueued
   }

Using RabbitMQ
^^^^^^^^^^^^^^

Assuming you want to enqueue a message on a queue named ``default``,
publish a persistent message to that queue in RabbitMQ.

Using Redis
^^^^^^^^^^^

Assuming you want to enqueue a message on a queue named ``default``,
run::

  > HSET default.msgs $YOUR_MESSAGE_ID $YOUR_MESSAGE_PAYLOAD
  > RPUSH default $YOUR_MESSAGE_ID


Prometheus Metrics
------------------

Prometheus metrics are automatically exported by workers whenever you
boot them using the command line utility.  By default, the exposition
server listens on port ``9191`` so you can tell Prometheus to scrape
that or you can specify what host and port it should listen on by
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
