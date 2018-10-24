from .middleware import Middleware


class DeclareQueuesMiddleware(Middleware):
    def after_worker_boot(self, broker, _):
        broker.declare_prepared_queues()

    def before_enqueue(self, broker, *_):
        broker.declare_prepared_queues()
