class Middleware:
    """Base class for broker middleware.  The default implementations
    for all hooks are no-ops and subclasses may implement whatever
    subset of hooks they like.
    """

    def before_acknowledge(self, queue_name):
        """Called before a message is acknowledged.
        """

    def after_acknowledge(self, queue_name):
        """Called after a message has been acknowledged.
        """

    def before_declare_actor(self, actor):
        """Called before an actor is declared.
        """

    def after_declare_actor(self, actor):
        """Called after an actor has been declared.
        """

    def before_declare_queue(self, queue_name):
        """Called before a queue is declared.
        """

    def after_declare_queue(self, queue_name):
        """Called before a queue has been declared.
        """

    def before_enqueue(self, message):
        """Called before a message is enqueued.
        """

    def after_enqueue(self, message):
        """Called after a message has been enqueued.
        """

    def before_process_message(self, message):
        """Called before a message is processed.
        """

    def after_process_message(self, message, *, result=None, exception=None):
        """Called after a message has been processed.
        """
