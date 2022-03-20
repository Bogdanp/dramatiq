.. References

.. |AgeLimit| replace:: :class:`AgeLimit<dramatiq.middleware.AgeLimit>`
.. |Barriers| replace:: :class:`Barriers<dramatiq.rate_limits.Barrier>`
.. |Brokers| replace:: :class:`Brokers<dramatiq.Broker>`
.. |Broker| replace:: :class:`Broker<dramatiq.Broker>`
.. |Callbacks| replace:: :class:`Callbacks<dramatiq.middleware.Callbacks>`
.. |CurrentMessage| replace:: :class:`CurrentMessage<dramatiq.middleware.CurrentMessage>`
.. |DramatiqError| replace:: :class:`DramatiqError<dramatiq.DramatiqError>`
.. |Encoders| replace:: :class:`Encoders<dramatiq.Encoder>`
.. |GenericActors| replace:: :class:`class-based actors<dramatiq.GenericActor>`
.. |Groups| replace:: :func:`Groups<dramatiq.group>`
.. |Interrupt| replace:: :class:`Interrupt<dramatiq.middleware.Interrupt>`
.. |MemcachedRLBackend| replace:: :class:`Memcached<dramatiq.rate_limits.backends.MemcachedBackend>`
.. |Messages| replace:: :class:`Messages<dramatiq.Message>`
.. |MiddlewareError| replace:: :class:`MiddlewareError<dramatiq.middleware.MiddlewareError>`
.. |Prometheus| replace:: :class:`Prometheus<dramatiq.middleware.Prometheus>`
.. |RabbitmqBroker_join| replace:: :meth:`join<dramatiq.brokers.rabbitmq.RabbitmqBroker.join>`
.. |RabbitmqBroker| replace:: :class:`RabbitmqBroker<dramatiq.brokers.rabbitmq.RabbitmqBroker>`
.. |RateLimitExceeded| replace:: :class:`RateLimitExceeded<dramatiq.RateLimitExceeded>`
.. |RateLimiters| replace:: :class:`RateLimiters<dramatiq.rate_limits.RateLimiter>`
.. |RedisBroker| replace:: :class:`RedisBroker<dramatiq.brokers.redis.RedisBroker>`
.. |RedisRLBackend| replace:: :class:`Redis<dramatiq.rate_limits.backends.RedisBackend>`
.. |RedisResBackend| replace:: :class:`Redis<dramatiq.results.backends.RedisBackend>`
.. |ResultBackends| replace:: :class:`ResultBackends<dramatiq.results.ResultBackend>`
.. |ResultBackend| replace:: :class:`ResultBackend<dramatiq.results.ResultBackend>`
.. |ResultFailure| replace:: :class:`ResultFailure<dramatiq.results.ResultFailure>`
.. |ResultMissing| replace:: :class:`ResultMissing<dramatiq.results.ResultMissing>`
.. |ResultTimeout| replace:: :class:`ResultTimeout<dramatiq.results.ResultTimeout>`
.. |Results| replace:: :class:`Results<dramatiq.results.Results>`
.. |Retries| replace:: :class:`Retries<dramatiq.middleware.Retries>`
.. |ShutdownNotifications| replace:: :class:`ShutdownNotifications<dramatiq.middleware.ShutdownNotifications>`
.. |Shutdown| replace:: :class:`Shutdown<dramatiq.middleware.Shutdown>`
.. |SkipMessage| replace:: :class:`SkipMessage<dramatiq.middleware.SkipMessage>`
.. |StubBroker_flush_all| replace:: :meth:`StubBroker.flush_all<dramatiq.brokers.stub.StubBroker.flush_all>`
.. |StubBroker_flush| replace:: :meth:`StubBroker.flush<dramatiq.brokers.stub.StubBroker.flush>`
.. |StubBroker_join| replace:: :meth:`StubBroker.join<dramatiq.brokers.stub.StubBroker.join>`
.. |StubBroker| replace:: :class:`StubBroker<dramatiq.brokers.stub.StubBroker>`
.. |TimeLimitExceeded| replace:: :class:`TimeLimitExceeded<dramatiq.middleware.TimeLimitExceeded>`
.. |TimeLimit| replace:: :class:`TimeLimit<dramatiq.middleware.TimeLimit>`
.. |URLRabbitmqBroker| replace:: :class:`URLRabbitmqBroker<dramatiq.brokers.rabbitmq.URLRabbitmqBroker>`
.. |WindowRateLimiter| replace:: :class:`WindowRateLimiter<dramatiq.rate_limits.WindowRateLimiter>`
.. |Worker_join| replace:: :meth:`Worker.join<dramatiq.Worker.join>`
.. |Worker_pause| replace:: :meth:`Worker.pause<dramatiq.Worker.pause>`
.. |Worker_resume| replace:: :meth:`Worker.resume<dramatiq.Worker.resume>`
.. |Worker| replace:: :meth:`Worker<dramatiq.Worker>`
.. |actor| replace:: :func:`actor<dramatiq.actor>`
.. |add_middleware| replace:: :meth:`add_middleware<dramatiq.Broker.add_middleware>`
.. |after_skip_message| replace:: :meth:`after_skip_message<dramatiq.Middleware.after_skip_message>`
.. |before_consumer_thread_shutdown| replace:: :meth:`before_consumer_thread_shutdown<dramatiq.Middleware.before_consumer_thread_shutdown>`
.. |before_worker_thread_shutdown| replace:: :meth:`before_worker_thread_shutdown<dramatiq.Middleware.before_worker_thread_shutdown>`
.. |dramatiq| replace:: :mod:`dramatiq`
.. |get_current_message| replace:: :meth:`get_current_message<dramatiq.middleware.CurrentMessage.get_current_message>`
.. |group| replace:: :func:`group<dramatiq.group>`
.. |pipeline_get_results| replace:: :meth:`get_results<dramatiq.pipeline.get_results>`
.. |pipeline_get_result| replace:: :meth:`get_result<dramatiq.pipeline.get_result>`
.. |pipeline| replace:: :func:`pipeline<dramatiq.pipeline>`
.. |rate_limits| replace:: :mod:`dramatiq.rate_limits`
.. |send_with_options| replace:: :meth:`send_with_options<dramatiq.Actor.send_with_options>`
.. |send| replace:: :meth:`send<dramatiq.Actor.send>`

.. _gevent: http://www.gevent.org/
.. _Memcached: http://memcached.org
.. _RabbitMQ: https://www.rabbitmq.com
.. _Redis: https://redis.io
