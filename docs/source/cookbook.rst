.. include:: global.rst

Cookbook
========

This part of the docs contains recipes for various things you might
want to do using dramatiq.  Each section will be light on prose and
code heavy, so if you have any questions about one of the recipes,
open an `issue on GitHub`_ or ask around on Gitter_.

.. _issue on GitHub: https://github.com/Bogdanp/dramatiq/issues
.. _Gitter: https://gitter.im/dramatiq/dramatiq


Reporting errors with Rollbar
-----------------------------

Rollbar_ provides an easy-to-use Python client.  Add it to your
project with pipenv_::

   $ pipenv install rollbar

Save the following middleware to a module inside your project:

.. code-block:: python
   :caption: myapp.rollbar_middleware

   import dramatiq
   import rollbar

   class RollbarMiddleware(dramatiq.Middleware):
       def after_process_message(self, broker, message, *, result=None, exception=None):
           if exception is not None:
               rollbar.report_exc_info()

Finally, instantiate and add it to your broker:

.. code-block:: python
   :caption: myapp.main

   rollbar.init(YOUR_ROLLBAR_KEY)
   broker.add_middleware(path.to.RollbarMiddleware())


.. _pipenv: https://docs.pipenv.org
.. _Rollbar: https://github.com/rollbar/pyrollbar#quick-start


Reporting errors with Sentry
----------------------------

Install Sentry's raven_ client with pipenv_::

   $ pipenv install raven

Save the following middleware to a module inside your project:

.. code-block:: python
   :caption: myapp.sentry_middleware

   import dramatiq

   class SentryMiddleware(dramatiq.Middleware):
       def __init__(self, raven_client):
           self.raven_client = raven_client

       def after_process_message(self, broker, message, *, result=None, exception=None):
           if exception is not None:
               self.raven_client.captureException()

Finally, instantiate and add it to your broker:

.. code-block:: python
   :caption: myapp.main

   from raven import Client

   raven_client = Client(YOUR_DSN)
   broker.add_middleware(path.to.SentryMiddleware(raven_client))


.. _pipenv: https://docs.pipenv.org
.. _raven: https://github.com/getsentry/raven-python
