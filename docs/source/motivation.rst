.. include:: global.rst

Motivation
==========

Remoulade's primary reason for being is the fact that I wanted a
distributed task queueing library that is simple and has sane defaults
for most SaaS workloads.  In that sense, it draws a lot of inspiration
from `GAE Push Queues`_ and Sidekiq_.

Remoulade's driving principles are as follows:

* high reliability and performance
* simple and easy to understand core
* convention over configuration

If you've ever had to use Celery in anger, Remoulade could be the tool
for you.


.. _GAE Push Queues: https://cloud.google.com/appengine/docs/standard/python/taskqueue/push/
.. _Sidekiq: http://sidekiq.org


Compared to *
-------------

I've used Celery_ professionally for years and my growing frustration
with it is one of the reasons why I developed remoulade.  Here are some
of the main differences between Remoulade, Celery and RQ:

+------------------------------+----------+-------------+--------------+
|                              | Remoulade | Celery_     | RQ_          |
+------------------------------+----------+-------------+--------------+
| Python 2 support             | No       | Yes         | Yes          |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Reliable delivery            | Yes      | No [#]_     | No           |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Automatic retries            | Yes      | No          | No           |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Code auto-reload             | Yes      | No          | No           |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Delayed tasks                | Yes      | Yes [#]_    | No           |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Locks and rate limiting      | Yes      | No          | No           |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Result storage               | Yes      | Yes         | Yes          |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Simple implementation        | Yes      | No [#sim]_  | Yes          |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Task prioritization          | Yes      | No [#prio]_ | No [#prio]_  |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| RabbitMQ support             | Yes      | Yes         | No           |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| Redis support                | Yes      | Yes         | Yes          |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+
| In-memory broker support     | Yes      | No          | No           |
|                              |          |             |              |
+------------------------------+----------+-------------+--------------+

.. [#] Celery acks tasks as soon as they’re pulled by a worker by
       default.  This is easy to change, but a bad default.  Remoulade
       doesn’t let you change this: tasks are only ever acked when
       they’re done processing.

.. [#] Celery has poor support for delayed tasks.  Delayed tasks are
       put on the same queue that is used for normal tasks and they’re
       simply pulled into worker memory until they can be executed,
       making it hard to autoscale workers by queue size.  Remoulade
       enqueues delayed tasks on a separate queue and moves them back
       when they're ready to be executed.

.. [#sim] Celery's source code is spread across 3 different projects
          (celery, billiard and kombu) and it’s impenetrable.  Its
          usage of runtime stack frame manipulation leads to
          heisenbugs.

.. [#prio] Celery and RQ don't support task prioritization.  You have
           to deploy multiple sets of workers in order to prioritize
           queues.  Remoulade lets you prioritize down to the
           individual |Actor| level.


.. _Celery: http://celeryproject.org
.. _RQ: http://python-rq.org/
