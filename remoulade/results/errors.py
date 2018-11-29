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

from ..errors import RemouladeError


class ResultError(RemouladeError):
    """Base class for result errors.
    """


class ResultTimeout(ResultError):
    """Raised when waiting for a result times out.
    """


class ResultMissing(ResultError):
    """Raised when a result can't be found.
    """


class ErrorStored(ResultError):
    """Raised when an error is stored in the result backend and raise_on_error is True
    """


class ParentFailed(ResultError):
    """Error stored when a parent actor in the pipeline failed
    """
