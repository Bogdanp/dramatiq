.. include:: global.rst

Changelog
=========

All notable changes to this project will be documented in this file.


`Unreleased`_
-------------

Added
^^^^^

* Support for pluggable message |Encoders|.


`0.15.1`_ -- 2017-12-08
-----------------------

Fixed
^^^^^

* Autoreload now works under gevent.


`0.15.0`_ -- 2017-11-24
-----------------------

Added
^^^^^

* Support for |Results|.
* ``pool`` parameter to the |MemcachedRLBackend| rate limiter backend.
* ``client`` parameter to the |RedisRLBackend| rate limiter backend.
* ``--watch-use-polling`` command line argument.

Fixed
^^^^^

* Fixed bad file descriptor issue during RMQ broker shutdown under gevent.


`0.14.0`_ -- 2017-11-21
-----------------------

Added
^^^^^

* :attr:`dramatiq.Actor.logger`.
* Logging statements before and after an actor is called.

Fixed
^^^^^

* |GenericActors| behave more like normal Python classes now. (`#15`_)

.. _#15: https://github.com/Bogdanp/dramatiq/issues/15


`0.13.1`_ -- 2017-11-17
-----------------------

Changed
^^^^^^^

* Connection and import errors that occur during process boot now log
  stack traces (`@rakanalh`_).
* Added support for Python **3.5** (`#7`_ by `@jssuzanne`_).

.. _@rakanalh: https://github.com/rakanalh
.. _@jssuzanne: https://github.com/jssuzanne
.. _#7: https://github.com/Bogdanp/dramatiq/issues/7


`0.13.0`_ -- 2017-11-15
-----------------------

Added
^^^^^

* Support for |GenericActors| (`#9`_).

.. _#9: https://github.com/Bogdanp/dramatiq/issues/9


`0.12.1`_ -- 2017-11-15
-----------------------

Fixed
^^^^^

* An ``AssertionError`` after starting the consumer if RabbitMQ is not
  running (`#10`_).

.. _#10: https://github.com/Bogdanp/dramatiq/issues/10


`0.12.0`_ -- 2017-11-14
-----------------------

Added
^^^^^

* |Worker_pause| and |Worker_resume|.
* ``url`` parameter to |RedisBroker|.

Fixed
^^^^^

* Pending interrupt messages are now removed from pika's queue before
  cancel is called.  This fixes an issue where an ``AtrributeError``
  was sometimes raised on worker shutdown.
* Pika connection reset logs from the main thread are now hidden.
* Distribution of ``dramatiq-gevent`` (`#2`_).

.. _#2: https://github.com/Bogdanp/dramatiq/issues/2


`0.11.0`_ -- 2017-11-09
-----------------------

Added
^^^^^

* |SkipMessage| middleware error.
* |after_skip_message| middleware hook.
* |RabbitmqBroker_join| now takes optional ``min_successes`` and
  ``idle_time`` parameters.

Changed
^^^^^^^

* Consumer reconnect backoff factor has been lowered from 10s to 100ms.
* |URLRabbitmqBroker| is now a factory function that creates instances
  of |RabbitmqBroker|.

Fixed
^^^^^

* Worker processes no longer use a spinlock to consume messages.
* Consumers now use the same idle timeout as workers.
* |StubBroker| no longer declares dead letter queues.


`0.10.2`_ -- 2017-11-06
-----------------------

Changed
^^^^^^^

* ``pika`` is now pinned to ``>=0.10,<0.12``.


`0.10.1`_ -- 2017-11-04
-----------------------

Added
^^^^^

* More benchmarks.

Fixed
^^^^^

* |StubBroker_flush_all| now flushes delay queues.


`0.10.0`_ -- 2017-10-30
-----------------------

Added
^^^^^

* |URLRabbitmqbroker| (`@whalesalad`_).
* StubBroker |StubBroker_flush| and |StubBroker_flush_all|.
* |before_consumer_thread_shutdown| middleware hook.
* |before_worker_thread_shutdown| middleware hook.

Changed
^^^^^^^

* Implementation of the window rate limiter has been streamlined.
* Redis requeue is now more efficient.
* RabbitMQ enqueue is now resilient to disconnects.

Fixed
^^^^^

* ``dramatiq-gevent`` packaging (`@bendemaree`_).

.. _@bendemaree: https://github.com/bendemaree
.. _@whalesalad: https://github.com/whalesalad


`0.9.0`_ -- 2017-10-20
----------------------

Changed
^^^^^^^

* Messages are no longer assigned new ids when they are re-enqueued.
  This makes tracking messages using middleware significantly easier.
* The RedisBroker now assigns its own internal message ids.


`0.8.0`_ -- 2017-10-19
----------------------

Changed
^^^^^^^

* RabbitmqBroker no longer takes a ConnectionParameters param as
  input.  Instead, it builds one based on kwargs.
* ``exec`` is now used to reload the main process on source code
  changes when the ``--watch`` flag is enabled.


`0.7.1`_ -- 2017-10-08
----------------------

Fixed
^^^^^

* Lua files are now properly distributed with the package.


`0.7.0`_ -- 2017-09-13
----------------------

Changed
^^^^^^^

* Reworked scheduled messages to improve fairness.  Messages are now
  re-enqueued on the broker once they hit their eta.
* ``prometheus-client`` has been pinned to version ``0.0.20``.


`0.6.1`_ -- 2017-07-20
----------------------

Fixed
^^^^^

* A race condition with calls to ``cas`` in the memcached rate limiter
  backend.


`0.6.0`_ -- 2017-07-09
----------------------

Added
^^^^^

* ``before`` and ``after`` arguments to |add_middleware|.
* Support for |RateLimiters|.


`0.5.2`_ -- 2017-06-29
----------------------

Changed
^^^^^^^

* Changed the default max retries value from ``None`` to ``20``,
  meaning tasks are now retried for up to about 30 days before they're
  dead-lettered by default.


`0.5.1`_ -- 2017-06-28
----------------------

Removed
^^^^^^^

* Dropped RabbitMQ heartbeat to avoid spurious disconnects.


`0.5.0`_ -- 2017-06-27
----------------------

Added
^^^^^

* Added ``dramatiq-gevent`` script.

Changed
^^^^^^^

* Capped prefetch counts to 65k.


.. _Unreleased: https://github.com/Bogdanp/dramatiq/compare/v0.15.1...HEAD
.. _0.15.1: https://github.com/Bogdanp/dramatiq/compare/v0.15.0...v0.15.1
.. _0.15.0: https://github.com/Bogdanp/dramatiq/compare/v0.14.0...v0.15.0
.. _0.14.0: https://github.com/Bogdanp/dramatiq/compare/v0.13.1...v0.14.0
.. _0.13.1: https://github.com/Bogdanp/dramatiq/compare/v0.13.0...v0.13.1
.. _0.13.0: https://github.com/Bogdanp/dramatiq/compare/v0.12.1...v0.13.0
.. _0.12.1: https://github.com/Bogdanp/dramatiq/compare/v0.12.0...v0.12.1
.. _0.12.0: https://github.com/Bogdanp/dramatiq/compare/v0.11.0...v0.12.0
.. _0.11.0: https://github.com/Bogdanp/dramatiq/compare/v0.10.2...v0.11.0
.. _0.10.2: https://github.com/Bogdanp/dramatiq/compare/v0.10.1...v0.10.2
.. _0.10.1: https://github.com/Bogdanp/dramatiq/compare/v0.10.0...v0.10.1
.. _0.10.0: https://github.com/Bogdanp/dramatiq/compare/v0.9.0...v0.10.0
.. _0.9.0: https://github.com/Bogdanp/dramatiq/compare/v0.8.0...v0.9.0
.. _0.8.0: https://github.com/Bogdanp/dramatiq/compare/v0.7.1...v0.8.0
.. _0.7.1: https://github.com/Bogdanp/dramatiq/compare/v0.7.0...v0.7.1
.. _0.7.0: https://github.com/Bogdanp/dramatiq/compare/v0.6.1...v0.7.0
.. _0.6.1: https://github.com/Bogdanp/dramatiq/compare/v0.6.0...v0.6.1
.. _0.6.0: https://github.com/Bogdanp/dramatiq/compare/v0.5.2...v0.6.0
.. _0.5.2: https://github.com/Bogdanp/dramatiq/compare/v0.5.1...v0.5.2
.. _0.5.1: https://github.com/Bogdanp/dramatiq/compare/v0.5.0...v0.5.1
.. _0.5.0: https://github.com/Bogdanp/dramatiq/compare/v0.4.1...v0.5.0
