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

**dramatiq** is a task queueing library for Python with a focus on
simplicity, reliability and performance.

Here's what it looks like:

::

  import dramatiq

  @dramatiq.actor
  def send_welcome_email(user_id):
    user = User.get_by_id(user_id)
    mailer = Mailer.get_mailer()
    mailer.send(to=user.email, subject="Welcome", body="Welcome to our website!")

  # ... somewhere in your signup process
  send_welcome_email.send(new_user.id)

**dramatiq** is :doc:`licensed<license>` under the AGPL and it
officially supports Python 3.6 and later.  Commercial licensing
options are available `upon request`_.

.. _upon request: mailto:bogdan@defn.io

Get It Now
----------

::

   $ pip install -U dramatiq[rabbitmq, watch]

Read the :doc:`quickstart` if you're ready to get started or check out
some of the :doc:`examples`.


User Guide
----------

This part of the documentation is focused primarily on teaching you
how to use dramatiq.

.. toctree::
   :maxdepth: 2

   installation
   quickstart
   examples
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
   license
