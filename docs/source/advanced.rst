.. include:: global.rst

Advanced Topics
===============

Brokers
-------

Multi-tenancy
^^^^^^^^^^^^^

With Remoulade you can run multiple logical apps on the same broker.
The way you do this is different for each broker, but fairly simple in
each case.

RabbitMQ
~~~~~~~~

RabbitMQ has the concept of `virtual hosts`_ built into it.  They
provide logical grouping and separation of resources.  You can create
virtual hosts using the `rabbitmqctl` command::

  $ rabbitmqctl add_vhost app1
  $ rabbitmqctl set_permissions -p app1 my_user ".*" ".*" ".*"

You can then pass that vhost to |RabbitmqBroker| when you instantiate it.

.. _virtual hosts:  https://www.rabbitmq.com/vhosts.html


Messages
--------

Message Persistence
^^^^^^^^^^^^^^^^^^^

Messages sent to Remoulade brokers are persisted to disk and survive
across broker reboots.  Exactly how often messages are flushed to disk
depends on your broker.

Messages that have been pulled by workers but not processed are
returned to the broker on graceful shutdown and any messages that are
in flight when a worker is terminated are going to be redelivered
later.  Messages are only ever acknowledged to (removed from) the
broker after they have been successfully processed.

When a worker goes down while processing messages (eg. due to
hardware, power or network failure) then the messages it pulled from
the broker will eventually be re-delivered to it (assuming it
recovers) or another worker.

Message Results
^^^^^^^^^^^^^^^

Remoulade can store actor return values to Redis by leveraging the |Results| middleware.
In most cases you can get by without needing this capability so the middleware is not turned on by
default. When you do need it, however, it's there.

.. _message-interrupts:

Message Interrupts
^^^^^^^^^^^^^^^^^^

Remoulade may interrupt message processing mid-execution.  This is
achieved by asynchronously raising an exception in the worker thread
that is currently processing the message.

.. attention::
   Currently, interrupts are only supported on CPython and are subject
   to the restrictions of the GIL.  This means the interupt exception
   will only be raised the next time that thread acquires the GIL, and
   they are unable to cancel system calls.

Interrupts are used by the following middleware:

* |ShutdownNotifications| (raises |Shutdown|)
* |TimeLimit| (raises |TimeLimitExceeded|)

In order to gracefully handle interrupts, wrap the code in a try/except
block, catching the appropriate exception type.  To attempt to requeue
the message, raise an exception to indicate failure.

.. code-block:: python

   import remoulade
   from remoulade.middleware import Interrupt

   @remoulade.actor(max_retries=3, notify_shutdown=True)
   def long_running_task():
       try:
           setup()
           do_work()
       except Shutdown:
           cleanup()
           raise


Enqueueing Messages from Other Languages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can enqueue Remoulade messages using any language that has bindings
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
~~~~~~~~~~~~~~

Assuming you want to enqueue a message on a queue named ``default``,
publish a persistent message to that queue in RabbitMQ.

Using Redis
~~~~~~~~~~~

Assuming you want to enqueue a message on a queue named ``default``,
run::

  > HSET default.msgs $YOUR_MESSAGE_ID $YOUR_MESSAGE_PAYLOAD
  > RPUSH default $YOUR_MESSAGE_ID


Workers
-------

Worker Exit Codes
^^^^^^^^^^^^^^^^^

Remoulade uses process exit codes to denote several scenarios:

=====  ========================================================================================
Code   Description
=====  ========================================================================================
``0``  Returned when the process exits gracefully.
``1``  Returned when the process is killed.
``2``  Returned when a module cannot be imported or when a command line argument is invalid.
``3``  Returned when a broker connection cannot be established during worker startup.
``4``  Returned when a PID file is set and Remoulade is already running.
=====  ========================================================================================

Controlling Workers
^^^^^^^^^^^^^^^^^^^

The main Remoulade process responds to several signals::

  $ kill -TERM [master-process-pid]

``INT`` and ``TERM``
~~~~~~~~~~~~~~~~~~~~

Sending an ``INT`` or ``TERM`` signal to the main process triggers
graceful shutdown.  Consumer threads will stop receiving new work and
worker threads will finish processing the work they have in flight
before shutting down.  Any tasks still in worker memory at this point
are re-queued on the broker.

If you send a second ``INT`` or ``TERM`` signal then the worker
processes will be killed immediately.

``HUP``
~~~~~~~

Sending ``HUP`` to the main process triggers a graceful shutdown
followed by a reload of the workers.  This is useful if you want to
reload code without completely restarting the main process.

Using gevent
^^^^^^^^^^^^

Remoulade comes with a CLI utility called ``remoulade-gevent`` that can
run workers under gevent_.  The following invocation would run 8
worker processes with 250 greenlets per process for a total of 2k
lightweight worker threads::

  $ remoulade-gevent my_app -p 8 -t 250

If your tasks spend most of their time doing network IO and don't
depend on C extensions to execute those network calls then using
gevent could provide a significant performance improvement.

I suggest at least experimenting with it to see if it fits your use
case.

Prometheus Metrics
^^^^^^^^^^^^^^^^^^

Prometheus metrics are automatically exported by workers whenever you
run them using the command line utility (assuming you're using the
Prometheus middleware).  By default, the exposition server listens on
port ``9191`` so you can tell Prometheus to scrape that or you can
specify what host and port it should listen on by setting the
``remoulade_prom_host`` and ``remoulade_prom_port`` environment
variables.

The following metrics are exported:

``remoulade_messages_total``
  A *counter* for the total number of messages processed.

``remoulade_message_errors_total``
  A *counter* for the total number of errored messages.

``remoulade_message_retries_total``
  A *counter* for the total number of retried messages.

``remoulade_message_rejects_total``
  A *counter* for the total number of dead-lettered messages.

``remoulade_messages_inprogress``
  A *gauge* for the number of messages currently being processed.

``remoulade_delayed_messages_inprogress``
  A *gauge* for the number of delayed messages currently in memory.

``remoulade_message_duration_milliseconds``
  A *histogram* for the time spent processing messages.

All metrics define labels for ``queue_name`` and ``actor_name``.

Grafana Dashboard
~~~~~~~~~~~~~~~~~

You can find a Grafana dashboard that displays these metrics here_.

.. _here: https://grafana.com/dashboards/3692

Gotchas with Prometheus
~~~~~~~~~~~~~~~~~~~~~~~

The Prometheus client for Python is a bit finicky when it comes to
exporting metrics from a multi-process configuration.  If your own app
uses Prometheus, then you should export ``prometheus_multiproc_dir``
and ``remoulade_prom_db`` environment variables -- both pointing to an
existing folder -- and remove any files in that folder before running
Remoulade.  For example::

  mkdir -p /tmp/remoulade-prometheus \
    && rm -r /tmp/remoulade-prometheus/* \
    && env prometheus_multiproc_dir=/tmp/remoulade-prometheus \
           remoulade_prom_db=/tmp/remoulade-prometheus \
           remoulade app

If you don't do this, then metrics will likely fail to export properly.
