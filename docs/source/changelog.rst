.. include:: global.rst

Changelog
=========

All notable changes to this project will be documented in this file.

`Unreleased`_
-------------

`1.17.1`_ -- 2024-10-26
-----------------------

Fixed
^^^^^

* `TimeLimit` middleware support for Python 3.13. (`#656`_, `#659`_,
  `@amureki`_)

.. _#656: https://github.com/Bogdanp/dramatiq/issues/656
.. _#659: https://github.com/Bogdanp/dramatiq/pull/659
.. _@amureki: https://github.com/amureki

Added
^^^^^

* The `Retries` middleware now supports an ``on_retries_exhausted``
  target actor to execute when retries on a message have been
  exhausted. (`#630`_, `@dbowring`_)

.. _#630: https://github.com/Bogdanp/dramatiq/pull/630
.. _@dbowring: https://github.com/dbowring

Changed
^^^^^^^

* The `actor` decorator now checks for duplicate actor names.
  (`#640`_, `#641`_, `@z0z0r4`_)
* The `Retries` middleware now tracks when a message was last requeued
  on retry. (`#629`_, `@kuba-lilz`_)

.. _#629: https://github.com/Bogdanp/dramatiq/pull/629
.. _#640: https://github.com/Bogdanp/dramatiq/issues/640
.. _#641: https://github.com/Bogdanp/dramatiq/pull/641
.. _@kuba-lilz: https://github.com/kuba-lilz
.. _@z0z0r4: https://github.com/z0z0r4


`1.17.0`_ -- 2024-05-09
-----------------------

Added
^^^^^

* Middleware hooks for after consumer & worker thread boot. (`#619`_,
  `@kamalmarhubi`_)
* Type hints for awaitable actors. (`#621`_, `@DABND19`_)

.. _#619: https://github.com/Bogdanp/dramatiq/pull/619
.. _#621: https://github.com/Bogdanp/dramatiq/pull/621
.. _@DABND19: https://github.com/DABND19
.. _@kamalmarhubi: https://github.com/kamalmarhubi

Changed
^^^^^^^

* The =watch= extras now require Watchdog version 4.0+.

Fixed
^^^^^

* The ``python_requires`` version in ``setup.py``. (`#606`_,
  `@niccodemus`_)
* The result middleware now takes message options into
  account. (`#612`_, `@huwylphimet`_)

.. _#606: https://github.com/Bogdanp/dramatiq/pull/606
.. _#612: https://github.com/Bogdanp/dramatiq/pull/612
.. _@niccodemus: https://github.com/nicoddemus
.. _@huwylphimet: https://github.com/huwylphimet


`1.16.0`_ -- 2024-01-25
-----------------------

Fixed
^^^^^

* The ``CurrentMessage`` middleware now works under AsyncIO. (`#586`_,
  `#593`_, `@pahrohfit`_)
* Improved logging behavior under different buffer modes. (`#596`_,
  `@5tefan`_)

.. _#586: https://github.com/Bogdanp/dramatiq/issues/586
.. _#593: https://github.com/Bogdanp/dramatiq/pull/593
.. _#596: https://github.com/Bogdanp/dramatiq/pull/596
.. _@pahrohfit: https://github.com/pahrohfit
.. _@5tefan: https://github.com/5tefan

Added
^^^^^

* CLI watcher now supports setting include and exclude patterns (`#594`_,
  `@nhairs`_)

.. _#594: https://github.com/Bogdanp/dramatiq/issues/594
.. _@nhairs: https://github.com/nhairs


`1.15.0`_ -- 2023-10-23
-----------------------

Fixed
^^^^^

* The ``global_broker`` variable is now type hinted. (`@jenstroeger`_)
* Pipeline result retrieval works with non-default brokers. (`#563`_,
  `#564`_, `@DiegoPomares`_)

.. _#563: https://github.com/Bogdanp/dramatiq/pull/563
.. _#564: https://github.com/Bogdanp/dramatiq/issues/564
.. _@DiegoPomares: https://github.com/DiegoPomares
.. _@jenstroeger: https://github.com/jenstroeger

Added
^^^^^

* Asyncio support. (`#536`_, `@caspervdw`_)
* Timedelta support for delay arguments. (`#569`_, `@h3nnn4n`_)

.. _#536: https://github.com/Bogdanp/dramatiq/pull/536
.. _#569: https://github.com/Bogdanp/dramatiq/pull/569
.. _@h3nnn4n: https://github.com/h3nnn4n

Changed
^^^^^^^

* Filesystem watcher no longer reloads dramatiq on file open events.
  (`#552`_, `@seanpile`_)
* The version bound on ``redis-py`` has been increased to include
  version 5.0. (`#567`_, `@scott-8`_)

.. _#552: https://github.com/Bogdanp/dramatiq/pull/552
.. _#567: https://github.com/Bogdanp/dramatiq/pull/567
.. _@caspervdw: https://github.com/caspervdw
.. _@scott-8: https://github.com/scott-8
.. _@seanpile: https://github.com/seanpile


`1.14.2`_ -- 2023-03-25
-----------------------

Fixed
^^^^^

* Restored ``namedtuple`` instance methods on ``Message``. (`#538`_)

.. _#538: https://github.com/Bogdanp/dramatiq/pull/538


`1.14.1`_ -- 2023-02-25
-----------------------

Fixed
^^^^^

* Added missing ``py.typed`` file to distributions. (`#531`_)

.. _#531: https://github.com/Bogdanp/dramatiq/pull/531


`1.14.0`_ -- 2023-02-05
-----------------------

Removed
^^^^^^^

* Dropped Python 3.6 support as it reached end-of-life

Changed
^^^^^^^

* Added Python 3.11 support to CI builds. (`#511`_, `@FinnLidbetter`_)
* Improved typing support.  ``Message`` is now a dataclass, but it
  should be compatible with the previous namedtuple-based
  implementation. (`#512`_, `#513`_, `#515`_, `#516`_, `@orsinium`_)

.. _#465: https://github.com/Bogdanp/dramatiq/issues/465
.. _#466: https://github.com/Bogdanp/dramatiq/pull/466
.. _#511: https://github.com/Bogdanp/dramatiq/pull/511
.. _#512: https://github.com/Bogdanp/dramatiq/pull/512
.. _#513: https://github.com/Bogdanp/dramatiq/pull/513
.. _#515: https://github.com/Bogdanp/dramatiq/pull/515
.. _#516: https://github.com/Bogdanp/dramatiq/pull/516
.. _@orsinium: https://github.com/orsinium


`1.13.0`_ -- 2022-04-02
-----------------------

Fixed
^^^^^

* A race condition in the Redis broker's ``join`` method. (`#480`_,
  `#481`_, `@CaselIT`_)
* Skipped messages and messages failed due to |AgeLimit| now store
  results more consistently. (`#440`_, `#449`_, `@FinnLidbetter`_)

.. _#440: https://github.com/Bogdanp/dramatiq/issues/440
.. _#449: https://github.com/Bogdanp/dramatiq/pull/449
.. _#480: https://github.com/Bogdanp/dramatiq/issues/480
.. _#481: https://github.com/Bogdanp/dramatiq/pull/481
.. _@CaselIT: https://github.com/CaselIT

Changed
^^^^^^^

* Typing support has been improved.  (`#482`_, `@staticdev`_)
* The default broker now falls back to Redis if the RabbitMQ extras
  are not installed, in an attempt to make the getting started process
  easier. (`#483`_, `#486`_, `@kurtmckee`_)

.. _#482: https://github.com/Bogdanp/dramatiq/issues/482
.. _#483: https://github.com/Bogdanp/dramatiq/issues/483
.. _#486: https://github.com/Bogdanp/dramatiq/pull/486
.. _@kurtmckee: https://github.com/kurtmckee
.. _@staticdev: https://github.com/staticdev


`1.12.3`_ -- 2022-01-16
-----------------------

Fixed
^^^^^

* An issue where signals remained blocked after worker process
  boot. (`#465`_, `#466`_, `@FinnLidbetter`_)

.. _#465: https://github.com/Bogdanp/dramatiq/issues/465
.. _#466: https://github.com/Bogdanp/dramatiq/pull/466


`1.12.2`_ -- 2022-01-14
-----------------------

Fixed
^^^^^

* An issue where stopping the process too quickly after boot could
  lead to an ``AttributeError``. (`#463`_, `#464`_, `@FinnLidbetter`_)

.. _#463: https://github.com/Bogdanp/dramatiq/issues/463
.. _#464: https://github.com/Bogdanp/dramatiq/pull/464

`1.12.1`_ -- 2021-12-19
-----------------------

Fixed
^^^^^

* Actors and messages can now specify 0 backoff.  (`@FinnLidbetter`_, `#438`_)
* An issue where Redis message ids could be put back onto the queue
  after ack/nack.  (`#442`_, `#444`_)

.. _#438: https://github.com/Bogdanp/dramatiq/pull/438
.. _#442: https://github.com/Bogdanp/dramatiq/issues/442
.. _#444: https://github.com/Bogdanp/dramatiq/pull/444

Removed
^^^^^^^

* Dropped Python 3.5 support as it reached end-of-life


`1.12.0`_ -- 2021-10-23
-----------------------

Added
^^^^^

* RabbitMQ messages now have a ``redelivered`` flag.  (`#405`_, `@nffdiogosilva`_)
* Time limits now work under gevent.  (`#408`_, `@FinnLidbetter`_)
* Shutdown notifications now work under gevent.  (`#426`_, `@FinnLidbetter`_)

.. _#405: https://github.com/Bogdanp/dramatiq/pull/405
.. _#408: https://github.com/Bogdanp/dramatiq/pull/408
.. _#426: https://github.com/Bogdanp/dramatiq/pull/426
.. _@FinnLidbetter: https://github.com/FinnLidbetter
.. _@nffdiogosilva: https://github.com/nffdiogosilva

Changed
^^^^^^^

* The ``watchdog`` library is no longer being pinned to a specific
  version.  (`#428`_)
* The redis broker now limits unpacks to half the size of the Lua
  stack.  (`#433`_, `#434`_, `@ethervoid`_)

.. _#428: https://github.com/Bogdanp/dramatiq/pull/428
.. _#433: https://github.com/Bogdanp/dramatiq/issues/433
.. _#434: https://github.com/Bogdanp/dramatiq/pull/434
.. _@ethervoid: https://github.com/ethervoid

Fixed
^^^^^

* Async exceptions now correctly set the thread id on Python 3.7 and
  up.  (`#419`_, `#420`_, `@FinnLidbetter`_)

.. _#419: https://github.com/Bogdanp/dramatiq/pull/419
.. _#420: https://github.com/Bogdanp/dramatiq/pull/420
.. _@FinnLidbetter: https://github.com/FinnLidbetter


`1.11.0`_ -- 2021-05-22
-----------------------

Added
^^^^^

* :meth:`decode<dramatiq.Message.decode>` now raises a new error,
  :class:`DecodeError<dramatiq.DecodeError>`, on exception. (`#375`_,
  `@thomazthz`_)

Changed
^^^^^^^

* The RabbitMQ broker moves messages that fail to decode to the
  DLQ. (`#375`_, `@thomazthz`_)

.. _#375: https://github.com/Bogdanp/dramatiq/pull/375
.. _@thomazthz: https://github.com/thomazthz

Fixed
^^^^^

* The Redis broker is now more defensive in how it handles
  re-enqueueing messages.  This should fix a potential race condition
  where a worker could hit its heartbeat timeout but still end up
  re-enqueueing messages (thus ending up with the same message id
  enqueued multiple times).  (`#266`_, `#395`_)
* A code path that could lead to an unbound variable error has now
  been fixed.  (`#382`_)
* Deleting the connection off of a ``RabbitMQ`` broker now correctly
  closes it and its associated channel (if any) before removing it
  from the broker. (`#381`_, `#384`_)

.. _#266: https://github.com/Bogdanp/dramatiq/issues/266
.. _#395: https://github.com/Bogdanp/dramatiq/pull/395
.. _#381: https://github.com/Bogdanp/dramatiq/issue/381
.. _#382: https://github.com/Bogdanp/dramatiq/issue/382
.. _#384: https://github.com/Bogdanp/dramatiq/issue/384


`1.10.0`_ -- 2020-12-21
-----------------------

Added
^^^^^

* The RabbitMQ broker dead message TTL can now be configured via the
  ``dramatiq_dead_message_ttl`` environment variable.  (`#354`_,
  `@evstratbg`_)
* The CLI now supports referencing a callable to set up the broker on
  worker startup.  (`#350`_)
* The ``--worker-shutdown-timeout`` flag.  (`#330`_, `@mic47`_)

.. _#330: https://github.com/Bogdanp/dramatiq/pull/330
.. _#350: https://github.com/Bogdanp/dramatiq/pull/350
.. _#354: https://github.com/Bogdanp/dramatiq/pull/354
.. _@evstratbg: https://github.com/evstratbg
.. _@mic47: https://github.com/mic47

Changed
^^^^^^^

* The CLI raises an error when the ``--watch`` flag is set on
  unsupported platforms. (`#326`_, `#328`_, `@CaselIT`_)

Fixed
^^^^^

* The CLI now returns code ``1`` when one of the workers is killed by
  an unhandled signal.  (`#334`_, `@omegacoleman`_)
* The results middleware now gracefully handles actor-not-found errors
  during nack. (`#336`_, `#337`_, `@AndreCimander`_)
* A memory bloat issue with tasks that raise exceptions.  (`#351`_)
* CI on Windows. (`#371`_, `@gdvalle`_)

.. _#326: https://github.com/Bogdanp/dramatiq/pull/326
.. _#328: https://github.com/Bogdanp/dramatiq/pull/328
.. _#334: https://github.com/Bogdanp/dramatiq/pull/334
.. _#336: https://github.com/Bogdanp/dramatiq/pull/336
.. _#337: https://github.com/Bogdanp/dramatiq/pull/337
.. _#351: https://github.com/Bogdanp/dramatiq/pull/351
.. _#371: https://github.com/Bogdanp/dramatiq/pull/371
.. _@AndreCimander: https://github.com/AndreCimander
.. _@CaselIT: https://github.com/CaselIT
.. _@gdvalle: https://github.com/gdvalle
.. _@omegacoleman: https://github.com/omegacoleman


`1.9.0`_ -- 2020-06-08
----------------------

Added
^^^^^

* A custom Redis connection can now be passed to the Redis broker via
  the new ``client`` keyword argument.  (`#274`_, `@davidt99`_)
* Message priority can now be changed in ``before_enqueue`` hooks.
  (`#313`_, `@thomazthz`_)
* Support for storing actor exceptions.  (`#156`_)
* Support for silent :class:`Retries<dramatiq.Retry>`.  (`#295`_)
* Support for expected exceptions via the ``throws`` actor option.
  (`#303`_, `@takhs91`_)
* Support for changing the consumer class in the RabbitMQ and Redis
  brokers.  (`#316`_, `@AndreCimander`_)

.. _#156: https://github.com/Bogdanp/dramatiq/issues/156
.. _#274: https://github.com/Bogdanp/dramatiq/issues/274
.. _#295: https://github.com/Bogdanp/dramatiq/issues/295
.. _#303: https://github.com/Bogdanp/dramatiq/issues/303
.. _#313: https://github.com/Bogdanp/dramatiq/issues/313
.. _#316: https://github.com/Bogdanp/dramatiq/issues/316
.. _@AndreCimander: https://github.com/AndreCimander
.. _@davidt99: https://github.com/davidt99
.. _@thomazthz: https://github.com/thomazthz

Changed
^^^^^^^

* Worker processes are no longer daemons.  (`#289`_, `#294`_, `@takhs91`_)

.. _#289: https://github.com/Bogdanp/dramatiq/pull/289
.. _#294: https://github.com/Bogdanp/dramatiq/pull/294
.. _@takhs91: https://github.com/takhs91

Fixed
^^^^^

* A race condition during command line startup where the wrong exit
  codes could be returned when subprocesses failed.  (`#286`_)
* A race condition between worker processes and fork processes during
  boot. (`#297`_)
* A logging race condition on Linux.  (`#171`_, `#286`_)
* ``fileno`` has been added to ``StreamablePipe``.  (`#291`_, `@takhs91`_)

.. _#171: https://github.com/Bogdanp/dramatiq/issues/286
.. _#286: https://github.com/Bogdanp/dramatiq/issues/286
.. _#291: https://github.com/Bogdanp/dramatiq/pull/291
.. _#297: https://github.com/Bogdanp/dramatiq/pull/297
.. _@takhs91: https://github.com/takhs91


`1.8.1`_ -- 2020-02-02
----------------------

Fixed
^^^^^

* An issue where an ``IndexError`` would be raised when multiple
  middlewre containing fork functions were defined.  (`#271`_)

.. _#271: https://github.com/Bogdanp/dramatiq/issues/271

`1.8.0`_ -- 2020-02-02
----------------------

Added
^^^^^

* Support for forking and running arbitrary functions (so-called "fork
  functions").  (`#127`_, `#230`_)
* The ``--fork-function`` flag.
* The ``--skip-logging`` flag.  (`#263`_, `@whalesalad`_)

.. _#263: https://github.com/Bogdanp/dramatiq/pull/263
.. _@whalesalad: https://github.com/whalesalad

Fixed
^^^^^

* An issue where the ``max_age`` parameter to |AgeLimit| was being
  ignored.  (`#240`_, `@evstratbg`_)
* An issue with delaying pipelines.  (`#264`_, `@synweap15`_)
* An issue where the master process would sometimes hang when stopped.
  (`#260`_, `@asavoy`_)
* An issue where the |RedisBroker| could sometimes prefetch more
  messages than it was configured to.  (`#262`_, `@benekastah`_)
* The |StubBroker| now flushes its dead letter queue when its
  ``flush_all`` method is called.  (`#247`_, `@CapedHero`_)
* The |RedisBroker| now takes the max lua stack size into account.
  This should fix certain heisenbugs that folks have encountered with
  that broker.  (`#259`_, `@benekastah`_)

.. _#240: https://github.com/Bogdanp/dramatiq/pull/240
.. _#247: https://github.com/Bogdanp/dramatiq/pull/247
.. _#259: https://github.com/Bogdanp/dramatiq/pull/259
.. _#260: https://github.com/Bogdanp/dramatiq/pull/260
.. _#262: https://github.com/Bogdanp/dramatiq/pull/262
.. _#264: https://github.com/Bogdanp/dramatiq/pull/264
.. _@CapedHero: https://github.com/CapedHero
.. _@asavoy: https://github.com/asavoy
.. _@benekastah: https://github.com/benekastah
.. _@evstratbg: https://github.com/evstratbg
.. _@synweap15: https://github.com/synweap15

Changed
^^^^^^^

* The |RabbitmqBroker| now creates its queues lazily.  (`#163`_, `#270`_, `@timdrijvers`_)
* The |Prometheus| middleware no longer depends on file locking to
  start its exposition server.  Instead, it uses the new fork
  functions functionality to start the server in a separate, unique
  process.  The middleware no longer takes any parameters.  While this
  would normally be a breaking change, it appears those parameters
  were previously ignored anyway.  (`#127`_, `#230`_)

.. _#127: https://github.com/Bogdanp/dramatiq/issues/127
.. _#163: https://github.com/Bogdanp/dramatiq/issues/163
.. _#230: https://github.com/Bogdanp/dramatiq/pull/230
.. _#270: https://github.com/Bogdanp/dramatiq/pull/270
.. _@timdrijvers: https://github.com/timdrijvers


`1.7.0`_ -- 2019-09-22
----------------------

Added
^^^^^

* Generic actors can now be passed custom actor registires.  (`#223`_, `@jonathanlintott`_)
* ``--use-spawn`` command line argument.  (`#227`_, `#228`_, `@jrusso1020`_)

Changed
^^^^^^^

* Uncaught exceptions within workers are now logged as errors rather
  than warnings.  (`#221`_, `@th0th`_)

.. _#221: https://github.com/Bogdanp/dramatiq/pull/221
.. _#223: https://github.com/Bogdanp/dramatiq/pull/223
.. _#227: https://github.com/Bogdanp/dramatiq/pull/227
.. _#228: https://github.com/Bogdanp/dramatiq/pull/228
.. _@jonathanlintott: https://github.com/jonathanlintott
.. _@jrusso1020: https://github.com/jrusso1020
.. _@th0th: https://github.com/th0th


`1.6.1`_ -- 2019-07-24
----------------------

Added
^^^^^

* |RabbitmqBroker| now supports multiple connection uris to be passed
  in via its ``url`` parameter.  (`#216`_, `@wsantos`_)

Changed
^^^^^^^

* Updated allowed version range for prometheus-client.  (`#219`_, `@robinro`_)

.. _#216: https://github.com/Bogdanp/dramatiq/pull/216
.. _#219: https://github.com/Bogdanp/dramatiq/pull/219
.. _@robinro: https://github.com/robinro
.. _@wsantos: https://github.com/wsantos


`1.6.0`_ -- 2019-05-02
----------------------

Added
^^^^^

* `dramatiq_queue_prefetch` environment variable to control the number
  of messages to prefetch per worker thread.  (`#183`_, `#184`_, `@xelhark`_)
* The RabbitMQ broker now retries the queue declaration process if an
  error occurs.  (`#179`_, `@davidt99`_)
* Support for accessing nested broker instances from the CLI.
  (`#191`_, `@bersace`_)
* Support for eagerly raising actor exceptions in the joining thread
  with the |StubBroker|.  (`#195`_, `#203`_)
* Support for accessing the current message from an actor via
  |CurrentMessage|.  (`#208`_)

.. _#179: https://github.com/Bogdanp/dramatiq/issues/179
.. _#183: https://github.com/Bogdanp/dramatiq/issues/183
.. _#184: https://github.com/Bogdanp/dramatiq/issues/184
.. _#191: https://github.com/Bogdanp/dramatiq/pull/191
.. _#195: https://github.com/Bogdanp/dramatiq/issues/195
.. _#203: https://github.com/Bogdanp/dramatiq/pull/203
.. _#208: https://github.com/Bogdanp/dramatiq/issues/208
.. _@bersace: https://github.com/bersace
.. _@davidt99: https://github.com/davidt99
.. _@xelhark: https://github.com/xelhark

Changed
^^^^^^^

* Pinned pika version `>1.0,<2.0`.  (`#202`_)

.. _#202: https://github.com/Bogdanp/dramatiq/pull/202

Fixed
^^^^^

* An issue where workers would fail and never recover after the
  connection to Redis was severed.  (`#207`_)
* ``pipe_ignore`` has been fixed to apply to the next message in line
  within a pipeline.  (`#194`_, `@metheoryt`_)

.. _#194: https://github.com/Bogdanp/dramatiq/pull/194
.. _#207: https://github.com/Bogdanp/dramatiq/issues/207
.. _@metheoryt: https://github.com/metheoryt


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


.. _Unreleased: https://github.com/Bogdanp/dramatiq/compare/v1.17.1...HEAD
.. _1.17.1: https://github.com/Bogdanp/dramatiq/compare/v1.17.0...v1.17.1
.. _1.17.0: https://github.com/Bogdanp/dramatiq/compare/v1.16.0...v1.17.0
.. _1.16.0: https://github.com/Bogdanp/dramatiq/compare/v1.15.0...v1.16.0
.. _1.15.0: https://github.com/Bogdanp/dramatiq/compare/v1.14.2...v1.15.0
.. _1.14.2: https://github.com/Bogdanp/dramatiq/compare/v1.14.1...v1.14.2
.. _1.14.1: https://github.com/Bogdanp/dramatiq/compare/v1.14.0...v1.14.1
.. _1.14.0: https://github.com/Bogdanp/dramatiq/compare/v1.13.0...v1.14.0
.. _1.13.0: https://github.com/Bogdanp/dramatiq/compare/v1.12.3...v1.13.0
.. _1.12.3: https://github.com/Bogdanp/dramatiq/compare/v1.12.2...v1.12.3
.. _1.12.2: https://github.com/Bogdanp/dramatiq/compare/v1.12.1...v1.12.2
.. _1.12.1: https://github.com/Bogdanp/dramatiq/compare/v1.12.0...v1.12.1
.. _1.12.0: https://github.com/Bogdanp/dramatiq/compare/v1.11.0...v1.12.0
.. _1.11.0: https://github.com/Bogdanp/dramatiq/compare/v1.10.0...v1.11.0
.. _1.10.0: https://github.com/Bogdanp/dramatiq/compare/v1.9.0...v1.10.0
.. _1.9.0: https://github.com/Bogdanp/dramatiq/compare/v1.8.1...v1.9.0
.. _1.8.1: https://github.com/Bogdanp/dramatiq/compare/v1.8.0...v1.8.1
.. _1.8.0: https://github.com/Bogdanp/dramatiq/compare/v1.7.0...v1.8.0
.. _1.7.0: https://github.com/Bogdanp/dramatiq/compare/v1.6.1...v1.7.0
.. _1.6.1: https://github.com/Bogdanp/dramatiq/compare/v1.6.0...v1.6.1
.. _1.6.0: https://github.com/Bogdanp/dramatiq/compare/v1.5.0...v1.6.0
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
