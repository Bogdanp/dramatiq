.. include:: global.rst

Cookbook
========

This part of the docs contains recipes for various things you might
want to do using dramatiq.  Each section will be light on prose and
code heavy, so if you have any questions about one of the recipes,
open an `issue on GitHub`_.

.. _issue on GitHub: https://github.com/Bogdanp/dramatiq/issues


Error Reporting
---------------

Reporting errors with Rollbar
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Rollbar_ provides an easy-to-use Python client.  Add it to your
project with pipenv_::

   $ pipenv install rollbar

Save the following middleware to a module inside your project:

.. code-block:: python

   import dramatiq
   import rollbar

   class RollbarMiddleware(dramatiq.Middleware):
     def after_process_message(self, broker, message, *, result=None, exception=None):
       if exception is not None:
         rollbar.report_exc_info()

Finally, instantiate and add it to your broker:

.. code-block:: python

   rollbar.init(YOUR_ROLLBAR_KEY)
   broker.add_middleware(path.to.RollbarMiddleware())


.. _pipenv: https://docs.pipenv.org
.. _Rollbar: https://github.com/rollbar/pyrollbar#quick-start

Reporting errors with Sentry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install Sentry's raven_ client with pipenv_::

   $ pipenv install raven

Save the following middleware to a module inside your project:

.. code-block:: python

   import dramatiq

   class SentryMiddleware(dramatiq.Middleware):
     def __init__(self, raven_client):
       self.raven_client = raven_client

     def after_process_message(self, broker, message, *, result=None, exception=None):
       if exception is not None:
         self.raven_client.captureException()

Finally, instantiate and add it to your broker:

.. code-block:: python

   from raven import Client

   raven_client = Client(YOUR_DSN)
   broker.add_middleware(path.to.SentryMiddleware(raven_client))


.. _pipenv: https://docs.pipenv.org
.. _raven: https://github.com/getsentry/raven-python


Frameworks
----------

API Star
^^^^^^^^

The `apistar_dramatiq`_ library lets you use API Star dependency
injection with your Dramatiq actors.

.. _apistar_dramatiq: https://github.com/Bogdanp/apistar_dramatiq
.. _API Star: https://github.com/encode/apistar


Django
^^^^^^

Check out the `django_dramatiq`_ project if you want to use Dramatiq
with Django_.  The `django_dramatiq_example`_ repo is an example app
build with Django and Dramatiq.

.. _django_dramatiq: https://github.com/Bogdanp/django_dramatiq
.. _django_dramatiq_example: https://github.com/Bogdanp/django_dramatiq_example
.. _django: https://djangoproject.com


Flask
^^^^^

The `flask_dramatiq_example`_ repo is an example app built with Flask_
and Dramatiq.

.. _flask_dramatiq_example: https://github.com/Bogdanp/flask_dramatiq_example
.. _flask: http://flask.pocoo.org


Operations
----------

Auto-discovering "tasks" modules with bash
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Dramatiq doesn't attempt to auto-discover tasks modules.  Assuming you
follow a convention where all your tasks modules are named
``tasks.py`` then you can discover them using bash:

.. code-block:: bash

   #!/usr/bin/env bash

   set -e

   tasks_packages=$(find . -type d -name tasks | sed s':/:.:g' | sed s'/^..//' | xargs)
   tasks_modules=$(find . -type f -name tasks.py | sed s':/:.:g' | sed s'/^..//' | sed s'/.py$//g' | xargs)
   all_modules="$tasks_packages $tasks_modules"

   echo "Discovered tasks modules:"
   for module in $all_modules; do
       echo "  * ${module}"
   done
   echo

   pipenv run dramatiq-gevent $all_modules --watch . --watch-use-polling

Retrying connection errors on startup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Dramatiq does not retry connection errors that occur on worker
startup.  It does, however, return a specific exit code (``3``) when
that happens.  Using that, you can build a wrapper script around it if
you need to retry with backoff when connection errors happen during
startup (eg. in Docker):

.. code-block:: bash

   #!/usr/bin/env bash

   delay=1
   while true; do
     dramatiq $@
     if [ $? -eq 3 ]; then
       echo "Connection error encountered on startup. Retrying in $delay second(s)..."
       sleep $delay
       delay=$((delay * 2))
     else
       exit $?
     fi
   done


Rate Limiting
-------------

Rate limiting work
^^^^^^^^^^^^^^^^^^

You can use dramatiq's |RateLimiters| to constrain actor concurrency.

.. code-block:: python

   import dramatiq
   import time

   from dramatiq.rate_limits import ConcurrentRateLimiter
   from dramatiq.rate_limits.backends import RedisBackend

   backend = RedisBackend()
   DISTRIBUTED_MUTEX = ConcurrentRateLimiter(backend, "distributed-mutex", limit=1)

   @dramatiq.actor
   def one_at_a_time():
     with DISTRIBUTED_MUTEX.acquire():
       time.sleep(1)
       print("Done.")

Whenever two ``one_at_a_time`` actors run at the same time, one of
them will be retried with exponential backoff.  This works by raising
an exception and relying on the built-in Retries middleware to do the
work of re-enqueueing the task.

If you want rate limiters not to raise an exception when they can't be
acquired, you should pass ``raise_on_failure=False`` to ``acquire``::

  with DISTRIBUTED_MUTEX.acquire(raise_on_failure=False) as acquired:
    if not acquired:
      print("Lock could not be acquired.")
    else:
      print("Lock was acquired.")


Results
-------

Storing message results
^^^^^^^^^^^^^^^^^^^^^^^

You can use dramatiq's result backends to store and retrieve message
return values.  To enable result storage, you need to instantiate and
add the |Results| middleware to your broker.

.. code-block:: python

   import dramatiq

   from dramatiq.brokers.rabbitmq import RabbitmqBroker
   from dramatiq.results.backends import RedisBackend
   from dramatiq.results import Results

   result_backend = RedisBackend()
   broker = RabbitmqBroker()
   broker.add_middleware(Results(backend=result_backend))
   dramatiq.set_broker(broker)

   @dramatiq.actor(store_results=True)
   def add(x, y):
     return x + y

   if __name__ == "__main__":
     message = add.send(1, 2)
     print(message.get_result(block=True))

Getting a result raises |ResultMissing| when a result hasn't been
stored yet or if it has already expired (results expire after 10
minutes by default).  When the ``block`` parameter is ``True``,
|ResultTimeout| is raised instead.
