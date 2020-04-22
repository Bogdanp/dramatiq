# This file is a part of Dramatiq.
#
# Copyright (C) 2020 CLEARTYPE SRL <bogdan@cleartype.io>
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

from .errors import ResultFailure

# We need to deal with backwards-compatibility here in case the user
# is migrating between dramatiq versions so the canary is used to
# detect exception results.
_CANARY = "dramatiq.results.Result"


def wrap_result(res):
    # This is a no-op for forwards-compatibility.  If the user deploys
    # a new version of dramatiq and then is forced to roll back, then
    # this will minimize the fallout.
    return res


def wrap_exception(e):
    return {
        "__t": _CANARY,
        "exn": {
            "type": type(e).__name__,
            "msg": str(e),
        }
    }


def unwrap_result(res):
    if isinstance(res, dict) and res.get("__t") == _CANARY:
        message = "actor raised %s: %s" % (res["exn"]["type"], res["exn"]["msg"])
        raise ResultFailure(message, res["exn"]["type"], res["exn"]["msg"])
    return res
