.. References

.. |dramatiq| replace:: :mod:`dramatiq`
.. |rate_limits| replace:: :mod:`dramatiq.rate_limits`
.. |actor| replace:: :func:`actor<dramatiq.actor>`
.. |send| replace:: :meth:`send<dramatiq.Actor.send>`
.. |send_with_options| replace:: :meth:`send_with_options<dramatiq.Actor.send_with_options>`
.. |add_middleware| replace:: :meth:`add_middleware<dramatiq.Broker.add_middleware>`
.. |RabbitmqBroker| replace:: :class:`RabbitmqBroker<dramatiq.brokers.rabbitmq.RabbitmqBroker>`
.. |RabbitmqBroker_join| replace:: :meth:`join<dramatiq.brokers.rabbitmq.RabbitmqBroker.join>`
.. |URLRabbitmqBroker| replace:: :class:`URLRabbitmqBroker<dramatiq.brokers.rabbitmq.URLRabbitmqBroker>`
.. |RedisBroker| replace:: :class:`RedisBroker<dramatiq.brokers.redis.RedisBroker>`
.. |StubBroker| replace:: :class:`StubBroker<dramatiq.brokers.stub.StubBroker>`
.. |StubBroker_flush| replace:: :meth:`flush<dramatiq.brokers.stub.StubBroker.flush>`
.. |StubBroker_flush_all| replace:: :meth:`flush_all<dramatiq.brokers.stub.StubBroker.flush_all>`
.. |TimeLimitExceeded| replace:: :class:`TimeLimitExceeded<dramatiq.middleware.TimeLimitExceeded>`
.. |RateLimiters| replace:: :class:`RateLimiters<dramatiq.rate_limits.RateLimiter>`
.. |before_consumer_thread_shutdown| replace:: :meth:`before_consumer_thread_shutdown<dramatiq.Middleware.before_consumer_thread_shutdown>`
.. |before_worker_thread_shutdown| replace:: :meth:`before_worker_thread_shutdown<dramatiq.Middleware.before_worker_thread_shutdown>`
.. |after_skip_message| replace:: :meth:`after_skip_message<dramatiq.Middleware.after_skip_message>`
.. |SkipMessage| replace:: :class:`SkipMessage<dramatiq.middleware.SkipMessage>`

.. _gevent: http://www.gevent.org/
.. _Memcached: http://memcached.org
.. _RabbitMQ: https://www.rabbitmq.com
.. _Redis: https://redis.io
