.. include:: global.rst

Dramatiq: simple task processing
================================

Release v\ |release|. (:doc:`installation`, :doc:`changelog`, `Discuss`_, `Source Code`_, `Support Dramatiq via Patreon`_, `Support Dramatiq via Tidelift`_)

.. _Discuss: https://reddit.com/r/dramatiq
.. _Source Code: https://github.com/Bogdanp/dramatiq
.. _Support Dramatiq via Patreon: https://patreon.com/popabogdanp
.. _Support Dramatiq via Tidelift: https://tidelift.com/subscription/pkg/pypi-dramatiq?utm_source=pypi-dramatiq&utm_medium=referral&utm_campaign=docs

.. image:: https://img.shields.io/badge/license-LGPL-blue.svg
   :target: license.html
.. image:: https://img.shields.io/badge/build-passing-brightgreen.svg
   :target: https://wdp9fww0r9.execute-api.us-west-2.amazonaws.com/production/results/Bogdanp/dramatiq
.. image:: https://badge.fury.io/py/dramatiq.svg
   :target: https://badge.fury.io/py/dramatiq
.. image:: https://tidelift.com/badges/github/Bogdanp/dramatiq
   :target: https://tidelift.com/subscription/pkg/pypi-dramatiq?utm_source=pypi-dramatiq&utm_medium=referral&utm_campaign=docs

**Dramatiq** is a distributed task processing library for Python with
a focus on simplicity, reliability and performance.

.. raw:: html

   <video width="660" src="https://media.defn.io/dramatiq.mp4" controls></video>

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
officially supports Python 3.5 and later.


Get It Now
----------

If you want to use it with RabbitMQ_::

   $ pip install -U 'dramatiq[rabbitmq, watch]'

Or if you want to use it with Redis_::

   $ pip install -U 'dramatiq[redis, watch]'

Read the :doc:`motivation` behind it or the :doc:`guide` if you're
ready to get started.

Support the Project
-------------------

If you use and love Dramatiq and want to make sure it gets the love
and attention it deserves then you should consider supporting the
project.  There are three ways in which you can do this right now:

1. If you're a company that uses Dramatiq in production then you can
   get a Tidelift_ subscription.  Doing so will give you an easy
   route to supporting both Dramatiq and other open source projects
   that you depend on.
2. If you're an individual or a company that doesn't want to go
   through Tidelift then you can support the project via Patreon_.
3. If you're a company and neither option works for you and you would
   like to receive an invoice from me directly then email me at
   bogdan@defn.io and let's talk.

.. _Tidelift: https://tidelift.com/subscription/pkg/pypi-dramatiq?utm_source=pypi-dramatiq&utm_medium=referral&utm_campaign=docs
.. _Patreon: https://patreon.com/popabogdanp


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
   Discussion Board <https://reddit.com/r/dramatiq>
   Support via Patreon <https://patreon.com/popabogdanp>
   Support via Tidelift <https://tidelift.com/subscription/pkg/pypi-dramatiq?utm_source=pypi-dramatiq&utm_medium=referral&utm_campaign=docs>
   license
