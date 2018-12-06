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
from ..broker import Broker
from ..results import Results
from ..results.backends import LocalBackend


class LocalBroker(Broker):
    """ Broker that calculate the message result immediately

    It can only be used with LocalBackend as a result backend
    """
    def __init__(self, middleware=None):
        super().__init__(middleware)

        # It use LocalBackend
        self.add_middleware(Results(backend=LocalBackend()))

    def add_middleware(self, middleware, *, before=None, after=None):
        if isinstance(middleware, Results) and not isinstance(middleware.backend, LocalBackend):
            raise RuntimeError("LocalBroker can only be used with LocalBackend.")
        super().add_middleware(middleware, before=before, after=after)

    def emit_before(self, signal, *args, **kwargs):
        # A local broker should not catch any exception because we are not in a worker but in the main thread
        for middleware in self.middleware:
            getattr(middleware, "before_" + signal)(self, *args, **kwargs)

    def emit_after(self, signal, *args, **kwargs):
        for middleware in reversed(self.middleware):
            getattr(middleware, "after_" + signal)(self, *args, **kwargs)

    def consume(self, queue_name, prefetch=1, timeout=100):
        raise ValueError('LocalBroker is not destined to use with a Worker')

    def declare_queue(self, queue_name):
        pass

    def enqueue(self, message, *, delay=None):
        """Enqueue and compute a message.

        Parameters:
          message(Message): The message to enqueue
          delay(int): ignored
        """
        actor = self.get_actor(message.actor_name)
        self.emit_before("process_message", message)
        res = actor(*message.args, **message.kwargs)
        self.emit_after("process_message", message, result=res)
        return message

    def flush(self, _):
        pass

    def flush_all(self):
        pass

    def join(self, *_):
        return
