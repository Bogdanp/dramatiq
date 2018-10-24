API Reference
=============

.. module:: remoulade


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
   :members:  __iter__, __next__, ack, nack, close
.. autoclass:: MessageProxy
   :members:
.. autoclass:: remoulade.brokers.rabbitmq.RabbitmqBroker
   :members:
   :inherited-members:
.. autoclass:: remoulade.brokers.redis.RedisBroker
   :members:
   :inherited-members:
.. autoclass:: remoulade.brokers.stub.StubBroker
   :members:
   :inherited-members:


Middleware
----------

The following middleware are all enabled by default.

.. autoclass:: Middleware
   :members:
   :member-order: bysource
.. autoclass:: remoulade.middleware.AgeLimit
.. autoclass:: remoulade.middleware.Callbacks
.. autoclass:: remoulade.middleware.Pipelines
.. autoclass:: remoulade.middleware.Prometheus
.. autoclass:: remoulade.middleware.Retries
.. autoclass:: remoulade.middleware.ShutdownNotifications
.. autoclass:: remoulade.middleware.TimeLimit

Errors
^^^^^^

The class hierarchy for middleware exceptions:

.. code-block:: none

    BaseException
    +-- Exception
    |   +-- remoulade.middleware.MiddlewareError
    |       +-- remoulade.middleware.SkipMessage
    +-- remoulade.middleware.Interrupt
        +-- remoulade.middleware.Shutdown
        +-- remoulade.middleware.TimeLimitExceeded


.. autoclass:: remoulade.middleware.MiddlewareError
.. autoclass:: remoulade.middleware.SkipMessage
.. autoclass:: remoulade.middleware.Interrupt
.. autoclass:: remoulade.middleware.TimeLimitExceeded
.. autoclass:: remoulade.middleware.Shutdown


Results
-------

Actor results can be stored and retrieved by leveraging result
backends and the results middleware.  Results and result backends are
not enabled by default and you should avoid using them until you have
a really good use case.  Most of the time you can get by with actors
simply updating data in your database instead of using results.

Middleware
^^^^^^^^^^

.. autoclass:: remoulade.results.Results

Backends
^^^^^^^^

.. autoclass:: remoulade.results.ResultBackend
.. autoclass:: remoulade.results.backends.MemcachedBackend
.. autoclass:: remoulade.results.backends.RedisBackend
.. autoclass:: remoulade.results.backends.StubBackend


Rate Limiters
-------------

Rate limiters can be used to determine whether or not an operation can
be run at the current time across many processes and machines by using
a shared storage backend.

Backends
^^^^^^^^

Rate limiter backends are used to store metadata about rate limits.

.. autoclass:: remoulade.rate_limits.RateLimiterBackend
.. autoclass:: remoulade.rate_limits.backends.MemcachedBackend
.. autoclass:: remoulade.rate_limits.backends.RedisBackend
.. autoclass:: remoulade.rate_limits.backends.StubBackend


Limiters
^^^^^^^^

.. autoclass:: remoulade.rate_limits.RateLimiter
   :members:
.. autoclass:: remoulade.rate_limits.BucketRateLimiter
.. autoclass:: remoulade.rate_limits.ConcurrentRateLimiter
.. autoclass:: remoulade.rate_limits.WindowRateLimiter


Workers
-------

.. autoclass:: Worker
   :members:


Errors
------

.. autoclass:: RemouladeError
   :members:
.. autoclass:: BrokerError
   :members:
.. autoclass:: ActorNotFound
   :members:
.. autoclass:: QueueNotFound
   :members:
.. autoclass:: ConnectionError
   :members:
.. autoclass:: ConnectionClosed
   :members:
.. autoclass:: ConnectionFailed
   :members:
.. autoclass:: RateLimitExceeded
   :members:
.. autoclass:: remoulade.results.ResultError
   :members:
.. autoclass:: remoulade.results.ResultMissing
   :members:
.. autoclass:: remoulade.results.ResultTimeout
   :members:
