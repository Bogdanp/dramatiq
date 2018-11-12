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

import warnings

from .local import LocalBackend
from .stub import StubBackend

try:
    from .redis import RedisBackend
except ImportError:  # pragma: no cover
    warnings.warn(
        "RedisBackend is not available.  Run `pip install remoulade[redis]` "
        "to add support for that backend.", ImportWarning,
    )

__all__ = ["StubBackend", "RedisBackend", "LocalBackend"]
