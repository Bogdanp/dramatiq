.. include:: global.rst

Changelog
=========

All notable changes to this project will be documented in this file.

[0.10.0] -- UNRELEASED
----------------------

Added
^^^^^

* |URLRabbitmqbroker| (`@whalesalad`_).
* StubBroker |StubBroker_flush| and |StubBroker_flush_all|.
* |before_consumer_thread_shutdown| middleware hook.
* |before_worker_thread_shutdown| middleware hook.

Changed
^^^^^^^

* Streamlined the implementation of the window rate limiter.
* Made requeue more efficient under Redis.
* Made enqueue resilient to disconnects under RabbitMQ.

Fixed
^^^^^

* ``dramatiq-gevent`` packaging (`@bendemaree`_).

.. _@bendemaree: https://github.com/bendemaree
.. _@whalesalad: https://github.com/whalesalad


[0.9.0] -- 2017-10-20
---------------------

Changed
^^^^^^^

* Messages are no longer assigned new ids when they are re-enqueued.
  This makes tracking messages using middleware significantly easier.
* The RedisBroker now assigns its own internal message ids.

[0.8.0] -- 2017-10-19
---------------------

Changed
^^^^^^^

* RabbitmqBroker no longer takes a ConnectionParameters param as
  input.  Instead, it builds one based on kwargs.
* ``exec`` is now used to reload the main process on source code
  changes when the ``--watch`` flag is enabled.

[0.7.1] -- 2017-10-08
---------------------

Fixed
^^^^^

* Fixed package distribution of Lua files.

[0.7.0] -- 2017-09-13
---------------------

Changed
^^^^^^^

* Reworked scheduled messages to improve fairness.  Messages are now
  re-enqueued on the broker once they hit their eta.
* Pinned ``prometheus-client`` to version ``0.0.20``.

[0.6.1] -- 2017-07-20
---------------------

Fixed
^^^^^

* A race condition with calls to ``cas`` in the memcached rate limiter
  backend.

[0.6.0] -- 2017-07-09
---------------------

Added
^^^^^

* ``before`` and ``after`` arguments to |add_middleware|.
* Support for |RateLimiters|.

[0.5.2] -- 2017-06-29
---------------------

Changed
^^^^^^^

* Changed the default max retries value from ``None`` to ``20``,
  meaning tasks are now retried for up to about 30 days before they're
  dead-lettered by default.

[0.5.1] -- 2017-06-28
---------------------

Removed
^^^^^^^

* Dropped RabbitMQ heartbeat to avoid spurious disconnects.

[0.5.0] -- 2017-06-27
---------------------

Added
^^^^^

* Added ``dramatiq-gevent`` script.

Changed
^^^^^^^

* Capped prefetch counts to 65k.
