.. include:: global.rst

Changelog
=========

v0.7.0
------

* Reworked scheduled messages to improve fairness.  Messages are now
  re-enqueued on the broker once they hit their eta.

v0.6.1
------

* Fixed a potential race condition with calls to ``cas`` in the
  memcached rate limiter backend.

v0.6.0
------

* Added ``before`` and ``after`` arguments to |add_middleware|.
* Added support for |RateLimiters|.

v0.5.2
------

* Changed the default max retries value from ``None`` to ``20``,
  meaning tasks are now retried for up to about 30 days before they're
  dead-lettered by default.

v0.5.1
------

* Dropped RabbitMQ heartbeat to avoid spurious disconnects.

v0.5.0
------

* Added ``dramatiq-gevent`` script.
* Capped prefetch counts to 65k.
