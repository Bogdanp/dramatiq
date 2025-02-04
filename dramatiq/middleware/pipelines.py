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

from .middleware import Middleware


class Pipelines(Middleware):
    """Middleware that lets you pipe actors together so that the
    output of one actor feeds into the input of another.

    Parameters:
      pipe_ignore(bool): When True, ignores the result of the previous
        actor in the pipeline.
      pipe_errorok(bool): When True, ignores the fact that the previous
        actor in the pipeline failed and runs anyway.
      pipe_target(dict): A message representing the actor the current
        result should be fed into.
    """

    @property
    def actor_options(self):
        return {
            "pipe_ignore",
            "pipe_errorok",
            "pipe_target",
        }

    def after_process_message(self, broker, message, *, result=None, exception=None):
        # Since Pipelines is a default middleware, this import has to
        # happen at runtime in order to avoid a cyclic dependency
        # from broker -> pipelines -> messages -> broker.
        from ..message import Message

        actor = broker.get_actor(message.actor_name)

        errorok = message.options.get("pipe_errorok") or actor.options.get("pipe_errorok")
        if (exception is not None or message.failed) and not errorok:
            return

        message_data = message.options.get("pipe_target")
        if message_data is not None:
            next_message = Message(**message_data)
            pipe_ignore = next_message.options.get("pipe_ignore") or actor.options.get("pipe_ignore")
            if not pipe_ignore:
                next_message = next_message.copy(args=next_message.args + (result,))

            broker.enqueue(next_message, delay=next_message.options.get("delay"))
