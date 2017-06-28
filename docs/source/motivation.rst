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
