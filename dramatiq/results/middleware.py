# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from ..errors import ActorNotFound
from ..logging import get_logger
from ..middleware import Middleware

#: The maximum amount of milliseconds results are allowed to exist in
#: the backend.
DEFAULT_RESULT_TTL = 600000


class Results(Middleware):
    """Middleware that automatically stores actor results.

    Example:

      >>> from dramatiq.results import Results
      >>> from dramatiq.results.backends import RedisBackend
      >>> backend = RedisBackend()
      >>> broker.add_middleware(Results(backend=backend))

      >>> @dramatiq.actor(store_results=True)
      ... def add(x, y):
      ...     return x + y

      >>> message = add.send(1, 2)
      >>> message.get_result(backend=backend)
      3

      >>> @dramatiq.actor(store_results=True)
      ... def fail():
      ...     raise Exception("failed")

      >>> message = fail.send()
      >>> message.get_result(backend=backend)
      Traceback (most recent call last):
        ...
      ResultFailure: actor raised Exception: failed

    Parameters:
      backend(ResultBackend): The result backend to use when storing
        results.
      store_results(bool): Whether or not actor results should be
        stored.  Defaults to False and can be set on a per-actor
        basis.
      result_ttl(int): The maximum number of milliseconds results are
        allowed to exist in the backend.  Defaults to 10 minutes and
        can be set on a per-actor basis.

    Warning:
      If you have retries turned on for an actor that stores results,
      then the result of a message may be delayed until its retries
      run out!
    """

    def __init__(self, *, backend=None, store_results=False, result_ttl=None):
        self.logger = get_logger(__name__, type(self))
        self.backend = backend
        self.store_results = store_results
        self.result_ttl = result_ttl or DEFAULT_RESULT_TTL

    @property
    def actor_options(self):
        return {
            "store_results",
            "result_ttl",
        }

    def _lookup_options(self, broker, message):
        try:
            actor = broker.get_actor(message.actor_name)
            store_results = actor.options.get("store_results", self.store_results)
            result_ttl = actor.options.get("result_ttl", self.result_ttl)
            return store_results, result_ttl
        except ActorNotFound:
            return False, 0

    def after_process_message(self, broker, message, *, result=None, exception=None):
        store_results, result_ttl = self._lookup_options(broker, message)
        if store_results and exception is None:
            self.backend.store_result(message, result, result_ttl)
        if not store_results \
           and result is not None \
           and message.options.get("pipe_target") is None:
            self.logger.warning(
                "Actor '%s' returned a value that is not None, but you "
                "haven't set its `store_results' option to `True' so "
                "the value has been discarded." % message.actor_name
            )

    def after_skip_message(self, broker, message):
        """If the message was skipped but not failed, then store None.
        Let after_nack handle the case where the message was skipped and failed.
        """
        store_results, result_ttl = self._lookup_options(broker, message)
        if store_results and not message.failed:
            self.backend.store_result(message, None, result_ttl)

    def after_nack(self, broker, message):
        store_results, result_ttl = self._lookup_options(broker, message)
        if store_results and message.failed:
            exception = message._exception or Exception("unknown")
            self.backend.store_exception(message, exception, result_ttl)
