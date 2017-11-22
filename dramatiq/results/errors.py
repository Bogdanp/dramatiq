from ..errors import DramatiqError


class ResultError(DramatiqError):
    """Base class for result errors.
    """


class ResultTimeout(ResultError):
    """Raised when waiting for a result times out.
    """


class ResultMissing(ResultError):
    """Raised when a result can't be found.
    """
