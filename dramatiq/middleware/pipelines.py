from .middleware import Middleware


class Pipelines(Middleware):
    """Middleware that lets you pipe actors together so that the
    output of one actor feeds into the input of another.

    Parameters:
      pipe_ignore(bool): When True, ignores the result of the previous
        actor in the pipeline.
      pipe_target(dict): A message representing the actor the current
        result should be fed into.
    """

    @property
    def actor_options(self):
        return {
            "pipe_ignore",
            "pipe_target",
        }

    def after_process_message(self, broker, message, *, result=None, exception=None):
        # Since Pipelines is a default middleware, this import has to
        # happen at runtime in order to avoid a cyclic dependency
        # from broker -> pipelines -> messages -> broker.
        from ..message import Message

        if exception is not None:
            return

        message_data = message.options.get("pipe_target")
        if message_data is not None:
            next_message = Message(**message_data)
            if not message.options.get("pipe_ignore", False):
                next_message = next_message.copy(args=next_message.args + (result,))

            broker.enqueue(next_message)
