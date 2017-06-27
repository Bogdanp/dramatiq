.. include:: global.rst

Advanced Usage
==============

Using gevent
------------

Dramatiq comes with a CLI utility called ``dramatiq-gevent`` that can
run workers under gevent_.  The following invocation would run 8
worker processes with 250 greenlets per process for a total of 2k
lightweight worker threads::

  $ dramatiq-gevent my_app -p 8 -t 200
