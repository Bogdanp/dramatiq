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
   :members:  __iter__, __next__, close
.. autoclass:: MessageProxy
   :members:
.. autoclass:: dramatiq.brokers.StubBroker
   :members:
.. autoclass:: dramatiq.brokers.RabbitmqBroker
   :members:


Middleware
----------

.. autoclass:: Middleware
   :members:
.. autoclass:: dramatiq.middleware.AgeLimit
   :members:
.. autoclass:: dramatiq.middleware.Prometheus
   :members:
.. autoclass:: dramatiq.middleware.Retries
   :members:
.. autoclass:: dramatiq.middleware.TimeLimit
   :members:


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
