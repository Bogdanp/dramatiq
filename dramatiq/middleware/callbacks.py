from .middleware import Middleware


class Callbacks(Middleware):
    """Middleware that lets you chain success and failure callbacks
    onto Actors.
    """

    @property
    def actor_options(self):
        return {
            "on_failure",
            "on_success",
        }

    def after_process_message(self, broker, message, *, result=None, exception=None):
        if exception is None:
            actor_name = message.options.get("on_success")
            if actor_name:
                actor = broker.get_actor(actor_name)
                actor.send(message.asdict(), result)

        else:
            actor_name = message.options.get("on_failure")
            if actor_name:
                actor = broker.get_actor(actor_name)
                actor.send(message.asdict(), {
                    "type": type(exception).__name__,
                    "message": str(exception),
                })
