.. include:: global.rst

Changelog
=========

All notable changes to this project will be documented in this file.

`Unreleased`_
-------------
* |message_get_result| has a forget parameter, if True, the result will be deleted from the result backend when
retrieved
* Remove support for memcached
* Log an error when an exception is raised while processing a message (previously it was a warning)


`0.2.0`_ -- 2018-11-09
----------------------

Changed
^^^^^^^

* |Results| now stores errors as well as results and will raise an |ErrorStored| the actor fail
* |message_get_result| has a raise_on_error parameter, True by default. If False, the method return |FAILURE_RESULT| if
there is no Error else raise an |ErrorStored|.
* |Middleware| have a ``default_before`` and  ``default_after`` to place them by default in the middleware list
* |Results| needs to be before |Retries|
* |Promotheus| removed from default middleware

`0.1.0`_ -- 2018-10-24
----------------------

Added
^^^^^

* A |LocalBroker| equivalent to CELERY_ALWAYS_EAGER.

Changed
^^^^^^^

* Name of project to Remoulade (fork of Dramatiq v1.3.0)
* Delete URLRabbitmqBroker
* Delete RedisBroker
* Set default max_retries to 0
* Declare RabbitMQ Queue on first message enqueuing

Fixed
^^^^^

* pipe_ignore was not recovered from right message

.. _Unreleased: https://github.com/wiremind/remoulade/compare/v0.2.0...HEAD
.. _0.2.0: https://github.com/wiremind/remoulade/releases/tag/v0.2.0
.. _0.1.0: https://github.com/wiremind/remoulade/releases/tag/v0.1.0
