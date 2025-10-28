.. include:: global.rst

API Reference
=============

.. module:: dramatiq


Functions
---------

.. autofunction:: get_broker
.. autofunction:: set_broker
.. autofunction:: get_encoder
.. autofunction:: set_encoder


Actors & Messages
-----------------

.. autofunction:: actor
.. autoclass:: Actor
   :members:
.. autoclass:: Message
   :members:

Class-based Actors
^^^^^^^^^^^^^^^^^^

.. autoclass:: GenericActor
   :members:

Message Composition
^^^^^^^^^^^^^^^^^^^

.. autoclass:: group
   :members:
.. autoclass:: pipeline
   :members:

Message Encoders
^^^^^^^^^^^^^^^^

Encoders are used to serialize and deserialize messages over the wire.

.. autoclass:: Encoder
   :members:
.. autoclass:: JSONEncoder
.. autoclass:: PickleEncoder


Brokers
-------

.. autoclass:: Broker
   :members:
.. autoclass:: Consumer
   :members:
.. autoclass:: MessageProxy
   :members:
.. autoclass:: dramatiq.brokers.rabbitmq.RabbitmqBroker
   :members:
   :inherited-members:
   :show-inheritance:
.. autoclass:: dramatiq.brokers.redis.RedisBroker
   :members:
   :inherited-members:
   :show-inheritance:
.. autoclass:: dramatiq.brokers.stub.StubBroker
   :members:
   :inherited-members:
   :show-inheritance:


Middleware
----------

Middleware Base Class
^^^^^^^^^^^^^^^^^^^^^

This defines the hooks available for middleware to implement,
and can be subclassed to implement custom middleware.

.. autoclass:: Middleware
   :members:
   :member-order: bysource

.. _default-middleware:

Default Middleware
^^^^^^^^^^^^^^^^^^

The following middleware classes are all enabled by default, with their default settings.

.. autoclass:: dramatiq.middleware.AgeLimit
.. autoclass:: dramatiq.middleware.Callbacks
.. autoclass:: dramatiq.middleware.Pipelines
.. autoclass:: dramatiq.middleware.Retries
.. autoclass:: dramatiq.middleware.ShutdownNotifications
.. autoclass:: dramatiq.middleware.TimeLimit

.. _optional-middleware:

Optional Middleware
^^^^^^^^^^^^^^^^^^^

The following middleware classes are available, but not enabled by default.

.. autoclass:: dramatiq.middleware.AsyncIO
.. autoclass:: dramatiq.middleware.CurrentMessage
   :members: get_current_message
   :member-order: bysource
.. autoclass:: dramatiq.middleware.prometheus.Prometheus

.. py:class:: dramatiq.results.Results
   :no-index:

   Middleware that automatically stores actor results.
   See :class:`dramatiq.results.Results` for details.

Middleware Errors
^^^^^^^^^^^^^^^^^

The class hierarchy for middleware exceptions:

.. code-block:: none

    BaseException
    +-- Exception
    |   +-- dramatiq.middleware.MiddlewareError
    |       +-- dramatiq.middleware.SkipMessage
    +-- dramatiq.middleware.Interrupt
        +-- dramatiq.middleware.Shutdown
        +-- dramatiq.middleware.TimeLimitExceeded


.. autoexception:: dramatiq.middleware.MiddlewareError
   :show-inheritance:
.. autoexception:: dramatiq.middleware.SkipMessage
   :show-inheritance:
.. autoexception:: dramatiq.middleware.Interrupt
   :show-inheritance:
.. autoexception:: dramatiq.middleware.TimeLimitExceeded
   :show-inheritance:
.. autoexception:: dramatiq.middleware.Shutdown
   :show-inheritance:


Results
-------

Actor results can be stored and retrieved by leveraging result
backends and the results middleware.  Results and result backends are
not enabled by default and you should avoid using them until you have
a really good use case.  Most of the time you can get by with actors
simply updating data in your database instead of using results.

Results Middleware
^^^^^^^^^^^^^^^^^^

.. autoclass:: dramatiq.results.Results

Results Backends
^^^^^^^^^^^^^^^^

.. autoclass:: dramatiq.results.ResultBackend
   :members:
.. autoclass:: dramatiq.results.backends.MemcachedBackend
   :show-inheritance:
.. autoclass:: dramatiq.results.backends.RedisBackend
   :show-inheritance:
.. autoclass:: dramatiq.results.backends.StubBackend
   :show-inheritance:


Rate Limiters
-------------

Rate limiters can be used to determine whether or not an operation can
be run at the current time across many processes and machines by using
a shared storage backend.

Rate Limiters Backends
^^^^^^^^^^^^^^^^^^^^^^

Rate limiter backends are used to store metadata about rate limits.

.. autoclass:: dramatiq.rate_limits.RateLimiterBackend
   :members:
.. autoclass:: dramatiq.rate_limits.backends.MemcachedBackend
   :show-inheritance:
.. autoclass:: dramatiq.rate_limits.backends.RedisBackend
   :show-inheritance:
.. autoclass:: dramatiq.rate_limits.backends.StubBackend
   :show-inheritance:


Limiters
^^^^^^^^

.. autoclass:: dramatiq.rate_limits.RateLimiter
   :members:
.. autoclass:: dramatiq.rate_limits.BucketRateLimiter
   :show-inheritance:
.. autoclass:: dramatiq.rate_limits.ConcurrentRateLimiter
   :show-inheritance:
.. autoclass:: dramatiq.rate_limits.WindowRateLimiter
   :show-inheritance:

Barriers
^^^^^^^^

.. autoclass:: dramatiq.rate_limits.Barrier
   :members:


Workers
-------

.. autoclass:: Worker
   :members:


Errors
------

.. autoexception:: DramatiqError
   :members:
   :show-inheritance:
.. autoexception:: BrokerError
   :members:
   :show-inheritance:
.. autoexception:: DecodeError
   :members:
   :show-inheritance:
.. autoexception:: ActorNotFound
   :members:
   :show-inheritance:
.. autoexception:: QueueNotFound
   :members:
   :show-inheritance:
.. autoexception:: ConnectionError
   :members:
   :show-inheritance:
.. autoexception:: ConnectionClosed
   :members:
   :show-inheritance:
.. autoexception:: ConnectionFailed
   :members:
   :show-inheritance:
.. autoexception:: RateLimitExceeded
   :members:
   :show-inheritance:
.. autoexception:: Retry
   :members:
   :show-inheritance:
.. autoexception:: dramatiq.results.ResultError
   :members:
   :show-inheritance:
.. autoexception:: dramatiq.results.ResultMissing
   :members:
   :show-inheritance:
.. autoexception:: dramatiq.results.ResultTimeout
   :members:
   :show-inheritance:
.. autoexception:: dramatiq.results.ResultFailure
   :members:
   :show-inheritance:

Environment Variables
---------------------

These are the environment variables that dramatiq reads

.. list-table::
   :header-rows: 1

   * - Name
     - Default
     - Description
   * - ``dramatiq_restart_delay``
     - 3000 (3 seconds)
     - The number of milliseconds to wait before restarting consumers after a connection error.
   * - ``dramatiq_queue_prefetch``
     - 2 times number of worker threads
     - The number of messages to prefetch from the queue for each worker process. In-progress messages are included in the count.
   * - ``dramatiq_delay_queue_prefetch``
     - 1000 times number of worker threads
     - The number of messages to prefetch from the delay queue for each worker.
   * - ``dramatiq_dead_message_ttl``
     - 604800000 (One week)
     - The maximum amount of time a message can be in the dead letter queue for the RabbitMQ Broker (in milliseconds).
   * - ``dramatiq_group_callback_barrier_ttl``
     - 86400000 (One day)
     -
   * - ``dramatiq_prom_db``
     - tempfile.gettempdir()/dramatiq-prometheus
     - The path to store the prometheus database files. See :ref:`gotchas-with-prometheus`.
   * - ``dramatiq_prom_host``
     - 0.0.0.0
     - See :ref:`prometheus-metrics`.
   * - ``dramatiq_prom_port``
     - 9191
     - See :ref:`prometheus-metrics`.
   * - ``dramatiq_worker_timeout``
     - 1000
     - The number of milliseconds workers should wake up after if the queue is idle.
