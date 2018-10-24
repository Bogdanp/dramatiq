.. include:: global.rst

Changelog
=========

All notable changes to this project will be documented in this file.



`1.0.0`_ -- 2018-10-24
----------------------

Added
^^^^^

* A |LocalBroker| equivalent to CELERY_ALWAYS_EAGER.

Changed
^^^^^^^

* Name of project to Remoulade
* Delete |URLRabbitmqBroker|
* Delete |RedisBroker|
* Set default |max_retries| to 0
* Declare RabbitMQ Queue on first message enqueuing

Fixed
^^^^^

* |pipe_ignore| was not recovered from right message