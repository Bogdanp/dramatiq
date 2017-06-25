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
.. autoclass:: dramatiq.middleware.AgeLimit
.. autoclass:: dramatiq.middleware.Prometheus
.. autoclass:: dramatiq.middleware.Retries
.. autoclass:: dramatiq.middleware.TimeLimit


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
