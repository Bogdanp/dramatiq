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

import time

from ..backend import ForgottenResult, Missing, ResultBackend


class StubBackend(ResultBackend):
    """An in-memory result backend.  For use in unit tests.

    Parameters:
      namespace(str): A string with which to prefix result keys.
      encoder(Encoder): The encoder to use when storing and retrieving
        result data.  Defaults to :class:`.JSONEncoder`.
    """

    results = {}

    def _get(self, message_key, forget: bool = False):
        if forget:
            data, expiration = self.results.get(message_key, (None, None))
            if data is not None:
                self.results[message_key] = self.encoder.encode(ForgottenResult.asdict()), expiration
        else:
            data, expiration = self.results.get(message_key, (None, None))

        if data is not None and time.monotonic() < expiration:
            return self.encoder.decode(data)
        return Missing

    def _store(self, message_key, result, ttl):
        result_data = self.encoder.encode(result)
        expiration = time.monotonic() + int(ttl / 1000)
        self.results[message_key] = (result_data, expiration)

    def increment_group_completion(self, group_id: str) -> int:
        group_completion_key = self.build_group_completion_key(group_id)
        completion = self.results.get(group_completion_key, 0) + 1
        self.results[group_completion_key] = completion
        return completion
