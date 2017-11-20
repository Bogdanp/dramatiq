from ..logging import get_logger
from ..middleware import Middleware

#: The maximum amount of milliseconds results are allowed to exist in
#: the backend.
RESULT_TTL = 600000


class Results(Middleware):
    """Middleware that automatically stores actor results.

    Parameters:
      backend(ResultBackend): The result backend to use when storing
        results.
      store_results(bool): Whether or not actor results should be
        stored.  Defaults to False and can be set on a per-actor
        basis.
    """

    def __init__(self, *, backend=None, store_results=False):
        self.logger = get_logger(__name__, type(self))
        self.backend = backend
        self.store_results = store_results

    @property
    def actor_options(self):
        return set([
            "store_results",
        ])

    def after_process_message(self, broker, message, *, result=None, exception=None):
        actor = broker.get_actor(message.actor_name)
        store_results = actor.options.get("store_results", self.store_results)
        if store_results and exception is None:
            self.backend.store_result(message, result, RESULT_TTL)
