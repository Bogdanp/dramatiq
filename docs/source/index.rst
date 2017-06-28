.. include:: global.rst

dramatiq: simple task processing
================================

Release v\ |release|. (:doc:`installation`, :doc:`changelog`)

.. image:: https://img.shields.io/badge/license-AGPL-blue.svg
   :target: license.html
.. image:: https://travis-ci.org/Bogdanp/dramatiq.svg?branch=master
   :target: https://travis-ci.org/Bogdanp/dramatiq
.. image:: https://codeclimate.com/github/Bogdanp/dramatiq/badges/coverage.svg
   :target: https://codeclimate.com/github/Bogdanp/dramatiq/coverage
.. image:: https://codeclimate.com/github/Bogdanp/dramatiq/badges/gpa.svg
   :target: https://codeclimate.com/github/Bogdanp/dramatiq
.. image:: https://badge.fury.io/py/dramatiq.svg
   :target: https://badge.fury.io/py/dramatiq
.. image:: https://img.shields.io/badge/Say%20Thanks!-%F0%9F%A6%89-1EAEDB.svg
   :target: https://saythanks.io/to/Bogdanp

**dramatiq** is a distributed task processing library for Python with
a focus on simplicity, reliability and performance.

Here's what it looks like:

::

  import dramatiq
  import requests

  @dramatiq.actor
  def count_words(url):
     response = requests.get(url)
     count = len(response.text.split(" "))
     print(f"There are {count} words at {url!r}.")

  # Synchronously count the words on example.com in the current process
  count_words("http://example.com")

  # or send the actor a message so that it may perform the count
  # later, in a separate process.
  count_words.send("http://example.com")

**dramatiq** is :doc:`licensed<license>` under the AGPL and it
officially supports Python 3.6 and later.  :doc:`commercial`
is also available.

.. _upon request: mailto:bogdan@defn.io

Get It Now
----------

If you want to use it with RabbitMQ_::

   $ pip install -U dramatiq[rabbitmq, watch]

Or if you want to use it with Redis_::

   $ pip install -U dramatiq[redis, watch]

Read the :doc:`motivation` behind it or the :doc:`guide` if you're
ready to get started.


User Guide
----------

This part of the documentation is focused primarily on teaching you
how to use dramatiq.

.. toctree::
   :maxdepth: 2

   installation
   motivation
   guide
   best_practices
   advanced


API Reference
-------------

This part of the documentation is focused on detailing the various
bits and pieces of the dramatiq developer interface.

.. toctree::
   :maxdepth: 2

   reference


Project Info
------------

.. toctree::
   :maxdepth: 1

   changelog
   contributing
   license
   commercial
