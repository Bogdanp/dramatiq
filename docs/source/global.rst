.. References

.. |Brokers| replace:: :class:`Brokers<remoulade.Broker>`
.. |Broker| replace:: :class:`Broker<remoulade.Broker>`
.. |Callbacks| replace:: :class:`Callbacks<remoulade.middleware.Callbacks>`
.. |RemouladeError| replace:: :class:`RemouladeError<remoulade.RemouladeError>`
.. |Encoders| replace:: :class:`Encoders<remoulade.Encoder>`
.. |GenericActors| replace:: :class:`class-based actors<remoulade.GenericActor>`
.. |Groups| replace:: :func:`Groups<remoulade.group>`
.. |Interrupt| replace:: :class:`Interrupt<remoulade.middleware.Interrupt>`
.. |Messages| replace:: :class:`Messages<remoulade.Message>`
.. |MiddlewareError| replace:: :class:`MiddlewareError<remoulade.middleware.MiddlewareError>`
.. |Prometheus| replace:: :class:`Prometheus<remoulade.middleware.Prometheus>`
.. |RabbitmqBroker_join| replace:: :meth:`join<remoulade.brokers.rabbitmq.RabbitmqBroker.join>`
.. |RabbitmqBroker| replace:: :class:`RabbitmqBroker<remoulade.brokers.rabbitmq.RabbitmqBroker>`
.. |RateLimitExceeded| replace:: :class:`RateLimitExceeded<remoulade.RateLimitExceeded>`
.. |RateLimiters| replace:: :class:`RateLimiters<remoulade.rate_limits.RateLimiter>`
.. |RedisRLBackend| replace:: :class:`Redis<remoulade.rate_limits.backends.RedisBackend>`
.. |RedisResBackend| replace:: :class:`Redis<remoulade.results.backends.RedisBackend>`
.. |ResultBackends| replace:: :class:`ResultBackends<remoulade.results.ResultBackend>`
.. |ResultBackend| replace:: :class:`ResultBackend<remoulade.results.ResultBackend>`
.. |ResultMissing| replace:: :class:`ResultMissing<remoulade.results.ResultMissing>`
.. |ResultTimeout| replace:: :class:`ResultTimeout<remoulade.results.ResultTimeout>`
.. |Results| replace:: :class:`Results<remoulade.results.Results>`
.. |Retries| replace:: :class:`Retries<remoulade.middleware.Retries>`
.. |ShutdownNotifications| replace:: :class:`ShutdownNotifications<remoulade.middleware.ShutdownNotifications>`
.. |Shutdown| replace:: :class:`Shutdown<remoulade.middleware.Shutdown>`
.. |SkipMessage| replace:: :class:`SkipMessage<remoulade.middleware.SkipMessage>`
.. |StubBroker_flush_all| replace:: :meth:`StubBroker.flush_all<remoulade.brokers.stub.StubBroker.flush_all>`
.. |StubBroker_flush| replace:: :meth:`StubBroker.flush<remoulade.brokers.stub.StubBroker.flush>`
.. |StubBroker_join| replace:: :meth:`StubBroker.join<remoulade.brokers.stub.StubBroker.join>`
.. |StubBroker| replace:: :class:`StubBroker<remoulade.brokers.stub.StubBroker>`
.. |TimeLimitExceeded| replace:: :class:`TimeLimitExceeded<remoulade.middleware.TimeLimitExceeded>`
.. |TimeLimit| replace:: :class:`TimeLimit<remoulade.middleware.TimeLimit>`
.. |WindowRateLimiter| replace:: :class:`WindowRateLimiter<remoulade.rate_limits.WindowRateLimiter>`
.. |Worker_join| replace:: :meth:`Worker.join<remoulade.Worker.join>`
.. |Worker_pause| replace:: :meth:`Worker.pause<remoulade.Worker.pause>`
.. |Worker_resume| replace:: :meth:`Worker.resume<remoulade.Worker.resume>`
.. |Worker| replace:: :meth:`Worker<remoulade.Worker>`
.. |actor| replace:: :func:`actor<remoulade.actor>`
.. |add_middleware| replace:: :meth:`add_middleware<remoulade.Broker.add_middleware>`
.. |after_skip_message| replace:: :meth:`after_skip_message<remoulade.Middleware.after_skip_message>`
.. |before_consumer_thread_shutdown| replace:: :meth:`before_consumer_thread_shutdown<remoulade.Middleware.before_consumer_thread_shutdown>`
.. |before_worker_thread_shutdown| replace:: :meth:`before_worker_thread_shutdown<remoulade.Middleware.before_worker_thread_shutdown>`
.. |remoulade| replace:: :mod:`remoulade`
.. |group| replace:: :func:`group<remoulade.group>`
.. |pipeline_result_get| replace:: :meth:`get<remoulade.CollectionResults.get>`
.. |pipeline| replace:: :func:`pipeline<remoulade.pipeline>`
.. |rate_limits| replace:: :mod:`remoulade.rate_limits`
.. |send_with_options| replace:: :meth:`send_with_options<remoulade.Actor.send_with_options>`
.. |send| replace:: :meth:`send<remoulade.Actor.send>`
.. |LocalBroker| replace:: :class:`LocalBroker<remoulade.brokers.local.LocalBroker>`
.. |ErrorStored| replace:: :class:`ErrorStored<remoulade.results.errors.ErrorStored>`
.. |message_get_result| replace:: :meth:`get_result<remoulade.message.get_result>`
.. |Middleware| replace:: :class:`Middleware<remoulade.Middleware>`
.. |FailureResult| replace:: :class:`FailureResult<remoulade.results.backend.FailureResult>`
.. |Result| replace:: :class:`Result<remoulade.Result>`
.. |GroupResults|  replace:: :class:`GroupResults<remoulade.composition_result>`
.. |get_result_backend|  replace:: :meth:`get_result_backend<remoulade.Broker.get_result_backend>`
.. |CollectionResults|  replace:: :class:`CollectionResults<remoulade.collection_results>`
.. |pipeline_results_get| replace:: :meth:`get<remoulade.CollectionResults.get>`





.. _gevent: http://www.gevent.org/
.. _RabbitMQ: https://www.rabbitmq.com
.. _Redis: https://redis.io
.. _Dramatiq: https://dramatiq.io
