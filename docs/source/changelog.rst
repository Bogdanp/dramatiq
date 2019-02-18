.. include:: global.rst

Changelog
=========

All notable changes to this project will be documented in this file.


`Unreleased`_
-------------


`1.5.0`_ -- 2019-02-18
----------------------

Added
^^^^^

* The RabbitMQ broker now supports native message priorities.  (`#157`_, `@davidt99`_)
* Support for specifying the actor class to |actor|.  (`#169`_, `@gilbsgilbs`_)

.. _#157: https://github.com/Bogdanp/dramatiq/pull/157
.. _#169: https://github.com/Bogdanp/dramatiq/pull/169
.. _@davidt99: https://github.com/davidt99
.. _@gilbsgilbs: https://github.com/gilbsgilbs

Changed
^^^^^^^

* Pika 0.13 is now required.

Fixed
^^^^^

* Consumers are now stopped after workers finish running their tasks.  (`#160`_, `@brownan`_)
* Worker logging on Python 3.7 is no longer delayed.

.. _#160: https://github.com/Bogdanp/dramatiq/pull/160
.. _@brownan: https://github.com/brownan


`1.4.3`_ -- 2019-01-08
----------------------

Fixed
^^^^^

* Changed license classifier to the correct license.  This is why you
  shouldn't publish changed before you've had coffee, folks!


`1.4.2`_ -- 2019-01-08
----------------------

Fixed
^^^^^

* License classifier in PyPI package.  There were no source code
  changes for this release.


`1.4.1`_ -- 2018-12-30
----------------------

Added
^^^^^

* Support for redis-py 3.x.  (`#142`_, `@maerteijn`_)

.. _#142: https://github.com/Bogdanp/dramatiq/pull/142
.. _@maerteijn: https://github.com/maerteijn

Fixed
^^^^^

* Workers wait for RMQ messages to be acked upon shutdown.  (`#148`_)
* Pipelines no longer continue when a message is failed.  (`#151`_, `@davidt99`_)
* Log files now work under Windows.  (`#141`_, `@ryansm1`_)

.. _#141: https://github.com/Bogdanp/dramatiq/pull/141
.. _#148: https://github.com/Bogdanp/dramatiq/issues/148
.. _#151: https://github.com/Bogdanp/dramatiq/issues/151
.. _@ryansm1: https://github.com/ryansm1
.. _@davidt99: https://github.com/davidt99


`1.4.0`_ -- 2018-11-25
----------------------

Added
^^^^^

* |Barriers|.

Changed
^^^^^^^

* ``cli.main`` now takes an optional argument namespace so that users
  may define their own entrypoints. (`#140`_, `@maerteijn`_)
* Actor "message received" and "completed in x ms" log messages are
  now logged with the ``DEBUG`` level instead of ``INFO`` level.  This
  improves throughput and makes logging much less verbose.
* The |TimeLimit| middleware no longer uses signals to trigger time
  limit handling.  Instead it uses a background thread per worker
  process.
* Dramatiq now shuts itself down if any of the workers die
  unexpectedly (for example, if one of them is killed by the OOM
  killer).
* Windows is now supported (with some caveats)! (`#119`_, `@ryansm1`_)

Fixed
^^^^^

* Allow ``pipe_ignore`` option to be set at the actor level.  (`#100`_)
* Result encoder now defaults to the global encoder.  (`#108`_, `@xdmiodz`_)
* Dot characters are now allowed in queue names. (`#111`_)
* Tests are now run on Windows. (`#113`_, `@ryansm1`_)

.. _#100: https://github.com/Bogdanp/dramatiq/issues/100
.. _#108: https://github.com/Bogdanp/dramatiq/issues/108
.. _#111: https://github.com/Bogdanp/dramatiq/issues/111
.. _#113: https://github.com/Bogdanp/dramatiq/issues/113
.. _#119: https://github.com/Bogdanp/dramatiq/issues/119
.. _#140: https://github.com/Bogdanp/dramatiq/issues/140
.. _@maerteijn: https://github.com/maerteijn
.. _@ryansm1: https://github.com/ryansm1
.. _@xdmiodz: https://github.com/xdmiodz


`1.3.0`_ -- 2018-07-05
----------------------

Changed
^^^^^^^

* Upgraded prometheus_client to 0.2.x.
* Bumped pika to version 0.12.  Because of this change, the
  ``interrupt`` method on |Broker| and its usages within |Worker| have
  been dropped.
* There is no longer a max message delay.

Fixed
^^^^^

* |Brokers| can now be passed an empty list of middleware.  (`#90`_)
* Potential stack overflow when restarting Consumer threads.  (`#89`_)

.. _#89: https://github.com/Bogdanp/dramatiq/issues/89
.. _#90: https://github.com/Bogdanp/dramatiq/issues/90


`1.2.0`_ -- 2018-05-24
----------------------

Added
^^^^^

* Support for worker heartbeats to |RedisBroker|.
* ``maintenance_chance`` and ``heartbeat_timeout`` parameters to
  |RedisBroker|.
* |Interrupt| base class for thread-interrupting exceptions. (`@rpkilby`_)
* |ShutdownNotifications| middleware. (`@rpkilby`_)

Changed
^^^^^^^

* |TimeLimitExceeded| is now a subclass of |Interrupt|.

Fixed
^^^^^

* |StubBroker_join| and |Worker_join| are now more reliable.
* Module import path is now prepended to search path rather than
  appended.  This fixes an issue where importing modules with the same
  name as modules from site-packages would end up importing the
  modules from site-packages. (`#88`_)
* |Prometheus| middleware no longer wipes the prometheus data
  directory on startup.  This fixes an issue with exporting
  application metrics along with worker metrics.

.. _#88: https://github.com/Bogdanp/dramatiq/issues/88

Deprecated
^^^^^^^^^^

* ``requeue_{deadline,interval}`` parameters to |RedisBroker|.  These
  two parameters no longer have any effect.

.. _@rpkilby: https://github.com/rpkilby


`1.1.0`_ -- 2018-04-17
----------------------

Added
^^^^^

* ``confirm_delivery`` parameter to |RabbitmqBroker|.
* ``dead_message_ttl``, ``requeue_deadline`` and ``requeue_interval``
  parameters to |RedisBroker|.
* ``url`` parameter to |RedisRLBackend| rate limiter backend.
* ``url`` parameter to |RedisResBackend| result backend.
* ``timeout`` parameter to all the brokers' ``join`` methods.  (`#57`_)
* ``flush`` and ``flush_all`` methods to |RedisBroker|.  (`#62`_)
* ``flush`` and ``flush_all`` methods to |RabbitmqBroker|.  (`#62`_)

Changed
^^^^^^^

* Cleaned up command line argument descriptions.

Deprecated
^^^^^^^^^^

* |URLRabbitmqBroker| is deprecated.  The |RabbitmqBroker| takes a
  ``url`` parameter so use that instead.  |URLRabbitmqBroker| will be
  removed in version 2.0.

Fixed
^^^^^

* ``rabbitmq`` and ``watch`` extra dependencies are only installed
  when they are explicitly required now.  (`#60`_, `@rpkilby`_)
* signal handling from the master process on FreeBSD 10.3.  (`#66`_)
* reloading now uses ``sys.executable`` when exec'ing workers that
  were started with ``python -m dramatiq``.
* an issue that caused logging to fail when non-utf-8 characters were
  printed to stdout/err.  (`#63`_)
* an issue with potentially drifting keys in the |WindowRateLimiter|.
  (`#69`_, `@gdvalle`_)

.. _#57: https://github.com/Bogdanp/dramatiq/issues/57
.. _#60: https://github.com/Bogdanp/dramatiq/issues/60
.. _#62: https://github.com/Bogdanp/dramatiq/issues/62
.. _#63: https://github.com/Bogdanp/dramatiq/issues/63
.. _#66: https://github.com/Bogdanp/dramatiq/issues/66
.. _#69: https://github.com/Bogdanp/dramatiq/issues/69
.. _@rpkilby: https://github.com/rpkilby
.. _@gdvalle: https://github.com/gdvalle


`1.0.0`_ -- 2018-03-31
----------------------

Added
^^^^^

* ``--log-file`` command line argument.  (`#43`_, `@najamansari`_)
* ``--pid-file`` command line argument.  (`#43`_, `@najamansari`_)

.. _#43: https://github.com/Bogdanp/dramatiq/issues/43
.. _@najamansari: https://github.com/najamansari

Changed
^^^^^^^

* Dramatiq is now licensed under the LGPL.

Fixed
^^^^^

* Passing ``time_limit`` in ``send_with_options``.  (`#44`_)

.. _#44: https://github.com/Bogdanp/dramatiq/issues/44


`0.20.0`_ -- 2018-03-17
-----------------------

Added
^^^^^

* ``--queues`` CLI argument.  (`#35`_)

.. _#35: https://github.com/Bogdanp/dramatiq/pull/35

Changed
^^^^^^^

* Unhandled errors within workers now print the full stack trace.
  (`#42`_)

.. _#42: https://github.com/Bogdanp/dramatiq/pull/42


`0.19.1`_ -- 2018-03-08
-----------------------

Fixed
^^^^^

* Calling ``str`` on |Actor|.  (`#40`_, `@aequitas`_)

.. _@aequitas: https://github.com/aequitas
.. _#40: https://github.com/Bogdanp/dramatiq/pull/40


`0.19.0`_ -- 2018-01-17
-----------------------

Added
^^^^^

* |group| and |pipeline|.
* ``retry_when`` parameter to |Retries|.

Changed
^^^^^^^

* |RateLimitExceeded| errors no longer log the full stack trace when
  raised within workers.
* Consumer connection errors no longer dump a stack trace.
* Consumers now wait exactly 3 seconds between retries after a
  connection error, rather than using exponential backoff.


`0.18.0`_ -- 2018-01-06
-----------------------

Added
^^^^^

* ``pip install dramatiq[all]`` installs all deps.
* ``--path`` command line argument.  (`#27`_)

Changed
^^^^^^^

* ``pip install dramatiq`` now installs RabbitMQ and watch deps.

.. _#27: https://github.com/Bogdanp/dramatiq/issues/27


`0.17.0`_ -- 2017-12-30
-----------------------

Added
^^^^^

* |Callbacks| middleware.
* ``asdict`` method to |Messages|.

Fixed
^^^^^

* Pinned pika version `0.11` to avoid an issue where passing
  ``heartbeat`` to ``RabbitmqBroker`` in ``get_broker`` would raise a
  ``TypeError``.  (`#23`_, `@chen2aaron`_)

.. _@chen2aaron: https://github.com/chen2aaron
.. _#23: https://github.com/Bogdanp/dramatiq/pull/23


`0.16.0`_ -- 2017-12-25
-----------------------

Added
^^^^^

* ``long_running`` example.
* ``scheduling`` example.
* |Messages| now support pluggable |Encoders|.
* |ResultBackends| now support pluggable |Encoders|.

Changed
^^^^^^^

* |RedisResBackend| result backend is now considerably more
  resource-efficient (it no longer polls).
* ``sys.std{err,out}`` are now redirected to stderr and line-buffered.

Fixed
^^^^^

* |TimeLimit| middleware now uses a monotonic clock.


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


.. _Unreleased: https://github.com/Bogdanp/dramatiq/compare/v1.5.0...HEAD
.. _1.5.0: https://github.com/Bogdanp/dramatiq/compare/v1.4.3...v1.5.0
.. _1.4.3: https://github.com/Bogdanp/dramatiq/compare/v1.4.2...v1.4.3
.. _1.4.2: https://github.com/Bogdanp/dramatiq/compare/v1.4.1...v1.4.2
.. _1.4.1: https://github.com/Bogdanp/dramatiq/compare/v1.4.0...v1.4.1
.. _1.4.0: https://github.com/Bogdanp/dramatiq/compare/v1.3.0...v1.4.0
.. _1.3.0: https://github.com/Bogdanp/dramatiq/compare/v1.2.0...v1.3.0
.. _1.2.0: https://github.com/Bogdanp/dramatiq/compare/v1.1.0...v1.2.0
.. _1.1.0: https://github.com/Bogdanp/dramatiq/compare/v1.0.0...v1.1.0
.. _1.0.0: https://github.com/Bogdanp/dramatiq/compare/v0.20.0...v1.0.0
.. _0.20.0: https://github.com/Bogdanp/dramatiq/compare/v0.19.1...v0.20.0
.. _0.19.1: https://github.com/Bogdanp/dramatiq/compare/v0.19.0...v0.19.1
.. _0.19.0: https://github.com/Bogdanp/dramatiq/compare/v0.19.0...v0.19.0
.. _0.18.0: https://github.com/Bogdanp/dramatiq/compare/v0.17.0...v0.18.0
.. _0.17.0: https://github.com/Bogdanp/dramatiq/compare/v0.16.0...v0.17.0
.. _0.16.0: https://github.com/Bogdanp/dramatiq/compare/v0.15.1...v0.16.0
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
