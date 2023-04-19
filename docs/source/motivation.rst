.. include:: global.rst

Motivation
==========

Dramatiq's primary reason for being is the fact that I wanted a
distributed task queueing library that is simple and has sane defaults
for most SaaS workloads.  In that sense, it draws a lot of inspiration
from `GAE Push Queues`_ and Sidekiq_.

Dramatiq's driving principles are as follows:

* high reliability and performance
* simple and easy to understand core
* convention over configuration

If you've ever had to use Celery in anger, Dramatiq could be the tool
for you.


.. _GAE Push Queues: https://cloud.google.com/appengine/docs/standard/python/taskqueue/push/
.. _Sidekiq: http://sidekiq.org


Compared to *
-------------

.. note::
   This section was last updated in 2019.  It's possible that various
   bits of the table below are now outdated.  Clarifications in PR form
   are always welcome!

I've used Celery_ professionally for years and my growing frustration
with it is one of the reasons why I developed dramatiq.  Here are some
of the main differences between Dramatiq, Celery, Huey and RQ:

+------------------------------+----------+---------------+--------------+--------------+
|                              | Dramatiq | Celery_       | Huey_        | RQ_          |
+------------------------------+----------+---------------+--------------+--------------+
| Python 2 support             | No       | Yes           | Yes          | Yes          |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Windows support              | Yes      | No            | Yes          | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Simple implementation        | Yes      | No [#sim]_    | Yes          | Yes          |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Automatic retries            | Yes      | No            | Yes          | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Reliable delivery            | Yes      | Optional [#]_ | No           | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Locks and rate limiting      | Yes      | No            | Yes          | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Task prioritization          | Yes      | No [#prio]_   | Yes          | Yes          |
|                              | [#prio]_ |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Delayed tasks                | Yes      | Yes [#]_      | Yes          | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Cronlike scheduling          | No       | Yes           | Yes          | No           |
|                              | [#cron]_ |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Chaining / Pipelining        | Yes      | Yes           | Yes          | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Result storage               | Yes      | Yes           | Yes          | Yes          |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Code auto-reload             | Yes      | No            | No           | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| RabbitMQ support             | Yes      | Yes           | Yes          | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Redis support                | Yes      | Yes           | Yes          | Yes          |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| In-memory broker support     | Yes      | No            | Yes          | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+
| Greenlet support             | Yes      | Yes           | Yes          | No           |
|                              |          |               |              |              |
+------------------------------+----------+---------------+--------------+--------------+

.. [#] Celery acks tasks as soon as they’re pulled by a worker by
       default.  This is easy to change, but a bad default.  Dramatiq
       doesn’t let you change this: tasks are only ever acked when
       they’re done processing.

.. [#] Celery has poor support for delayed tasks.  Delayed tasks are
       put on the same queue that is used for normal tasks and they’re
       simply pulled into worker memory until they can be executed,
       making it hard to autoscale workers by queue size.  Dramatiq
       enqueues delayed tasks on a separate queue and moves them back
       when they're ready to be executed.

.. [#sim] Celery's source code is spread across 3 different projects
          (celery, billiard and kombu) and it’s impenetrable.  Its
          usage of runtime stack frame manipulation leads to
          heisenbugs.

.. [#prio] Celery doesn't support task prioritization.  Dramatiq
           supports global prioritization under RabbitMQ via the
           ``broker_priority``.  It also provides worker-local
           prioritization of prefetched messages.

.. [#cron] For cron-like scheduling functionality, you can combine
           Dramatiq with APScheduler_ or Periodiq_. 3rd-party packages
           exist which implement this approach for various frameworks,
           like: Dramatiq-Crontab_


.. _Celery: http://celeryproject.org
.. _huey: https://huey.readthedocs.io/
.. _RQ: http://python-rq.org/
.. _APScheduler: https://apscheduler.readthedocs.io/
.. _Periodiq: https://gitlab.com/bersace/periodiq
.. _Dramatiq-Crontab: https://github.com/voiio/dramatiq-crontab
