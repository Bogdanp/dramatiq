import warnings

try:
    from .memcached import MemcachedBackend  # noqa
except ImportError:  # pragma: no cover
    warnings.warn(
        "MemcachedBackend is not available.  Run `pip install dramatiq[memcached]` "
        "to add support for that backend.", ImportWarning,
    )

try:
    from .redis import RedisBackend  # noqa
except ImportError:  # pragma: no cover
    warnings.warn(
        "RedisBackend is not available.  Run `pip install dramatiq[redis]` "
        "to add support for that backend.", ImportWarning,
    )
