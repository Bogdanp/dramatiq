.. include:: global.rst

Changelog
=========

All notable changes to this project will be documented in this file.

`Unreleased`_
-------------

Fixed
^^^^^

* Failure of children of pipeline when a message fail (in the case of pipeline of groups)

`0.7.0`_ -- 2018-12-04
----------------------

Added
^^^^^

* Support for |pipeline| with groups (result backend necessary for this)
* Added group_id to |group|

Changed
^^^^^^^
* Remove support for group of groups, a |group| take as input a |pipeline| or a message
* |get_result_backend| now raise NoResultBackend if there is no |ResultBackend|
* Merged PipelineResult and GroupResult into |CollectionResult|
* |message_get_result| on forgotten results now returns None
* Update redis-py to 3.0.1


`0.6.0`_ -- 2018-11-23
----------------------

Fixed
^^^^^

* Better handling of RabbitMQ queue declaration (consumer will keep trying on ConnectionError)

Changed
^^^^^^^

* Prevent access to |Message| result if the linked actor do not have store_results=True

Added
^^^^^

* Add Prefetch multiplier to cli parameters

`0.5.0`_ -- 2018-11-15
----------------------

Breaking Changes
^^^^^^^^^^^^^^^^
* Added property result to |Message| (type: |Result|), and |pipeline| (type: PipelineResult) and results to |group|
 (type: GroupResults). These new Class get the all result linked logic (get instead of get_result)
* Rename MessageResult to |Result|
* Removed get_results from |Message|, |group| and |pipeline| (and all results related methods
like completed_count, ...). Use the new result property for |Message| and |pipeline|, and results for |group|.

`0.4.0`_ -- 2018-11-15
----------------------

Changed
^^^^^^^

* Rename FAILURE_RESULT to |FailureResult| (for consistency)

Added
^^^^^

* Add MessageResult which can be created from a message_id and can be used to retrieved the result of the linked
message

Fixed
^^^^^

* Clear timer on before_process_stop

`0.3.0`_ -- 2018-11-12
----------------------

Changed
^^^^^^^

* |message_get_result| has a forget parameter, if True, the result will be deleted from the result backend when
retrieved
* Remove support for memcached
* Log an error when an exception is raised while processing a message (previously it was a warning)


`0.2.0`_ -- 2018-11-09
----------------------

Changed
^^^^^^^

* |Results| now stores errors as well as results and will raise an |ErrorStored| the actor fail
* |message_get_result| has a raise_on_error parameter, True by default. If False, the method return |FailureResult| if
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

.. _Unreleased: https://github.com/wiremind/remoulade/compare/v0.7.0...HEAD
.. _0.7.0: https://github.com/wiremind/remoulade/releases/tag/v0.7.0
.. _0.6.0: https://github.com/wiremind/remoulade/releases/tag/v0.6.0
.. _0.5.0: https://github.com/wiremind/remoulade/releases/tag/v0.5.0
.. _0.4.0: https://github.com/wiremind/remoulade/releases/tag/v0.4.0
.. _0.3.0: https://github.com/wiremind/remoulade/releases/tag/v0.3.0
.. _0.2.0: https://github.com/wiremind/remoulade/releases/tag/v0.2.0
.. _0.1.0: https://github.com/wiremind/remoulade/releases/tag/v0.1.0
