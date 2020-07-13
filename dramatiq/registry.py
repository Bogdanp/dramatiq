from .actor import Actor, _queue_name_re


class Registry:
    '''
    A Registry allows defining a collection of Actors not directly bound to a Broker.

    This allows your code to declar Actors before configuring a Broker.
    '''
    def __init__(self):
        self.actors = {}
        self.broker = None

    def actor(self, fn=None, *, actor_class=Actor, actor_name=None, queue_name="default", priority=0, **options):
        '''
        Mimics `actor.actor` decorator, but skips the actor options check, and passes `self` as broker.
        '''

        def decorator(fn):
            if not _queue_name_re.fullmatch(queue_name):
                raise ValueError(
                    "Queue names must start with a letter or an underscore followed "
                    "by any number of letters, digits, dashes or underscores."
                )

            return actor_class(
                fn,
                actor_name=actor_name or fn.__name__,
                queue_name=queue_name,
                priority=priority,
                broker=self,
                options=options,
            )

        if fn is None:
            return decorator
        return decorator(fn)

    def __getattr__(self, name):
        # Proxy everything else to our Broker, if set.
        return getattr(self.broker, name)

    def declare_actor(self, actor):
        '''
        Intercept when Actor class tries to register itself.
        '''
        if self.broker:
            self.broker.declare_actor(actor)
        else:
            self.actors[actor.actor_name] = actor

    def bind_broker(self, broker):
        self.broker = broker

        for actor_name, actor in self.actors.items():
            invalid_options = set(actor.options) - broker.actor_options
            if invalid_options:
                invalid_options_list = ", ".join(invalid_options)
                raise ValueError((
                    "Actor %s specified the following options which are not "
                    "supported by this broker: %s. Did you forget to add a "
                    "middleware to your Broker?"
                ) % (actor_name, invalid_options_list))

            broker.declar_actor(actor)
