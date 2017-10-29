.. include:: global.rst

Motivation
==========

Dramatiq's primary reason for being is the fact that I wanted a
distributed task queueing library that is simple and has sane defaults
for most SaaS workloads.  In that sense, it draws a lot of inspiration
from `GAE Push Queues`_ and Sidekiq_.

Dramatiq's driving principles are as follows:

* high reliability
* simple and easy to understand core
* convention over configuration

If you're used to either of those or if you've ever had to use Celery
in anger, Dramatiq might just be the tool for you.


.. _GAE Push Queues: https://cloud.google.com/appengine/docs/standard/python/taskqueue/push/
.. _Sidekiq: http://sidekiq.org


Compared to Celery
------------------

I've used Celery_ professionally for years and my growing frustration
with it is one of the reasons why I developed dramatiq.  Here are some
of the main differences between the two:

* Celery doesn't support code auto-reload.
* Celery doesn’t support task prioritization.  You have to deploy
  multiple sets of workers in order to prioritize queues.  Dramatiq
  lets you prioritize down to the individual |Actor| level.
* Celery has poor support for delayed tasks.  Delayed tasks are put on
  the same queue that is used for normal tasks and they’re simply
  pulled into worker memory until they can be executed, making it hard
  to autoscale workers by queue size.  Dramatiq enqueues delayed tasks
  on a separate queue and moves them back when they're ready to be
  executed.
* Celery acks tasks as soon as they’re pulled by a worker by default.
  This is easy to change, but a bad default.  Dramatiq doesn’t let you
  change this: tasks are only ever acked when they’re done processing.
* Celery tasks are not automatically retried on error.  Dramatiq
  retries with exponential backoff by default for up to 30 days.
* Celery’s not well suited for integration testing.  You’re expected
  to unit test tasks and to turn eager evaluation on for integration
  tests, but even then task exceptions will be swallowed by default.
  Dramatiq provides an in-memory stub broker for this use case.
* Celery's source code is spread across 3 different projects (celery,
  billiard and kombu) and it’s impenetrable.  Its usage of runtime
  stack frame manipulation leads to heisenbugs.
* Dramatiq doesn't have task result storage out of the box.
* Dramatiq gives you less control over task routing under RabbitMQ.

.. _Celery: http://celeryproject.org


Compared to RQ
--------------

Here are some notable differences between dramatiq and RQ_:

* Dramatiq supports RabbitMQ as a broker in addition to Redis.
* RQ messages are pickled so messages can't easily be enqueued from
  other languages.  Pickling represents a security hazard and is in
  opposition to the best practice of sending small, primitive messages
  over the network.
* RQ queue prioritization is handled like it is in Celery: you have to
  spawn multiple groups of workers.
* RQ forks for every job, making it slower.  Forks that are killed
  because they’ve surpassed their time limits can leak DB connections.
* RQ doesn't have a good integration testing story.

.. _RQ: http://python-rq.org/
