API Reference
=============

.. module:: dramatiq


Functions
---------

.. autofunction:: get_broker
.. autofunction:: set_broker


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


Brokers
-------

.. autoclass:: Broker
   :members:
.. autoclass:: Consumer
   :members:  __iter__, __next__, ack, nack, close
.. autoclass:: MessageProxy
   :members:
.. autoclass:: dramatiq.brokers.rabbitmq.RabbitmqBroker
   :members:
   :inherited-members:
.. autofunction:: dramatiq.brokers.rabbitmq.URLRabbitmqBroker
.. autoclass:: dramatiq.brokers.redis.RedisBroker
   :members:
   :inherited-members:
.. autoclass:: dramatiq.brokers.stub.StubBroker
   :members:
   :inherited-members:


Middleware
----------

.. autoclass:: Middleware
   :members:
   :member-order: bysource
.. autoclass:: dramatiq.middleware.SkipMessage
.. autoclass:: dramatiq.middleware.AgeLimit
.. autoclass:: dramatiq.middleware.Prometheus
.. autoclass:: dramatiq.middleware.Retries
.. autoclass:: dramatiq.middleware.TimeLimit
.. autoclass:: dramatiq.middleware.TimeLimitExceeded


Rate Limiters
-------------

Rate limiters can be used to determine whether or not an operation can
be run at the current time across many processes and machines by using
a shared storage backend.

Backends
^^^^^^^^

Rate limiter backends are used to store metadata about rate limits.

.. autoclass:: dramatiq.rate_limits.RateLimiterBackend
.. autoclass:: dramatiq.rate_limits.backends.MemcachedBackend
.. autoclass:: dramatiq.rate_limits.backends.RedisBackend


Limiters
^^^^^^^^

.. autoclass:: dramatiq.rate_limits.RateLimiter
   :members:
.. autoclass:: dramatiq.rate_limits.BucketRateLimiter
.. autoclass:: dramatiq.rate_limits.ConcurrentRateLimiter
.. autoclass:: dramatiq.rate_limits.WindowRateLimiter


Workers
-------

.. autoclass:: Worker
   :members:


Errors
------

.. autoclass:: DramatiqError
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
