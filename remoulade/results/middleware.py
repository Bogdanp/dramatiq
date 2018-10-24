# This file is a part of Remoulade.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Remoulade is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Remoulade is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ..logging import get_logger
from ..middleware import Middleware

#: The maximum amount of milliseconds results are allowed to exist in
#: the backend.
DEFAULT_RESULT_TTL = 600000


class Results(Middleware):
    """Middleware that automatically stores actor results.

    Example:

      >>> from remoulade.results import Results
      >>> from remoulade.results.backends import RedisBackend
      >>> backend = RedisBackend()
      >>> broker.add_middleware(Results(backend=backend))

      >>> @remoulade.actor(store_results=True)
      ... def add(x, y):
      ...   return x + y

      >>> message = add.send(1, 2)
      >>> message.get_result(backend=backend)
      3

    Parameters:
      backend(ResultBackend): The result backend to use when storing
        results.
      store_results(bool): Whether or not actor results should be
        stored.  Defaults to False and can be set on a per-actor
        basis.
      result_ttl(int): The maximum number of milliseconds results are
        allowed to exist in the backend.  Defaults to 10 minutes and
        can be set on a per-actor basis.
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

    def after_process_message(self, broker, message, *, result=None, exception=None):
        actor = broker.get_actor(message.actor_name)
        store_results = actor.options.get("store_results", self.store_results)
        result_ttl = actor.options.get("result_ttl", self.result_ttl)
        if store_results and exception is None:
            self.backend.store_result(message, result, result_ttl)
