from .middleware import Middleware


class DeclareQueuesMiddleware(Middleware):
    def before_consume(self, broker):
        broker.declare_prepared_queues()

    def before_enqueue(self, broker, *_):
        broker.declare_prepared_queues()
