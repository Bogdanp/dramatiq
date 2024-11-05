.. include:: global.rst

Dramatiq: background tasks
==========================

Release v\ |release|. (:doc:`installation`, :doc:`changelog`, `Discuss`_, `Source Code`_)

.. _Discuss: https://groups.io/g/dramatiq-users
.. _Source Code: https://github.com/Bogdanp/dramatiq

.. image:: https://img.shields.io/badge/license-LGPL-blue.svg
   :target: license.html
.. image:: https://github.com/Bogdanp/dramatiq/workflows/CI/badge.svg
   :target: https://github.com/Bogdanp/dramatiq/actions?query=workflow%3A%22CI%22
.. image:: https://badge.fury.io/py/dramatiq.svg
   :target: https://badge.fury.io/py/dramatiq

**Dramatiq** is a background task processing library for Python with a
focus on simplicity, reliability and performance.

.. raw:: html

   <video width="660" src="https://media.defn.io/dramatiq-2.mp4" controls></video>

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

**Dramatiq** is :doc:`licensed<license>` under the LGPL and it
officially supports Python 3.9 and later.


Get It Now
----------

If you want to use it with RabbitMQ_::

   $ pip install -U 'dramatiq[rabbitmq, watch]'

Or if you want to use it with Redis_::

   $ pip install -U 'dramatiq[redis, watch]'

Read the :doc:`motivation` behind it or the :doc:`guide` if you're
ready to get started.


User Guide
----------

This part of the documentation is focused primarily on teaching you
how to use Dramatiq.

.. toctree::
   :maxdepth: 2

   installation
   motivation
   guide
   best_practices
   troubleshooting
   advanced
   cookbook


API Reference
-------------

This part of the documentation is focused on detailing the various
bits and pieces of the Dramatiq developer interface.

.. toctree::
   :maxdepth: 2

   reference


Project Info
------------

.. toctree::
   :maxdepth: 1

   Source Code <https://github.com/Bogdanp/dramatiq>
   changelog
   Contributing <https://github.com/Bogdanp/dramatiq/blob/master/CONTRIBUTING.md>
   Discussion Board <https://groups.io/g/dramatiq-users>
   license
