.. include:: global.rst

Cookbook
========

This part of the docs contains recipes for various things you might
want to do using Remoulade.  Each section will be light on prose and
code heavy, so if you have any questions about one of the recipes,
open an `issue on GitHub`_.

.. _issue on GitHub: https://github.com/wiremind/remoulade/issues


Callbacks
---------

Remoulade has built-in support for sending actors messages when other
actors succeed or fail.  The ``on_failure`` callback is called every
time an actor fails, even if the message is going to be retried.

.. code-block:: python

   import remoulade

   @remoulade.actor
   def identity(x):
     return x

   @remoulade.actor
   def print_result(message_data, result):
     print(f"The result of message {message_data['message_id']} was {result}.")

   @remoulade.actor
   def print_error(message_data, exception_data):
     print(f"Message {message_data['message_id']} failed:")
     print(f"  * type: {exception_data['type']}")
     print(f"  * message: {exception_data['message']!r}")

   if __name__ == "__main__":
     identity.send_with_options(
       args=(42,)
       on_failure=print_error,
       on_success=print_result,
     )


Composition
-----------

Remoulade has built-in support for a couple high-level composition
constructs.  You can use these to combine generalized tasks that don't
know about one another into complex workflows.

In order to take advantage of group and pipeline result management,
you need to enable result storage and your actors need to store
results.  Check out the `Results`_ section for more information on
result storage.

Groups
^^^^^^

|Groups| run actors in parallel and let you gather their results or
wait for all of them to finish.  Assuming you have a computationally
intensive actor called ``frobnicate``, you can group multiple
messages together as follows::

  g = group([
    frobnicate.message(1, 2),
    frobnicate.message(2, 3),
    frobnicate.message(3, 4),
  ]).run()

This will enqueue 3 separate messages and, assuming there are enough
resources available, execute them in parallel.  You can then wait for
the whole group to finish::

  g.wait(timeout=10_000)  # 10s expressed in millis

Or you can iterate over the results::

  for res in g.results.get(block=True, timeout=5_000):
    ...

Results are returned in the same order that the messages were added to
the group.

Pipelines
^^^^^^^^^

Actors can be chained together using the |pipeline| function.  For
example, if you have an actor that gets the text contents of a website
and one that counts the number of "words" in a piece of text:

.. code-block:: python

   @remoulade.actor
   def get_uri_contents(uri):
     return requests.get(uri).text

   @remoulade.actor
   def count_words(uri, text):
     count = len(text.split(" "))
     print(f"There are {count} words at {uri}.")

You can chain them together like so::

  uri = "http://example.com"
  pipe = pipeline([
    get_uri_contents.message(uri),
    count_words.message(uri),
  ]).run()

Or you can use pipe notation to achieve the same thing::

  pipe = get_uri_contents.message(uri) | count_words.message(uri)

In both cases, the result of running ``get_uri_contents(uri)`` is
passed as the last positional argument to ``count_words``.  If you
would like to avoid passing the result of an actor to the next one in
line, set the ``pipe_ignore`` option to ``True`` when you create the
"receiving" message::

  (
    bust_caches.message() |
    prepare_codes.message_with_options(pipe_ignore=True) |
    launch_missiles.message()
  )

Here, the result of ``bust_caches()`` will not be passed to
``prepare_codes()``, but the result of ``prepare_codes()`` will be
passed to ``launch_missiles(codes)``.  To get the end result of a
pipeline -- that is, the result of the last actor in the pipeline --
you can call |pipeline_result_get|::

  pipe.result.get(block=True, timeout=5_000)

To get the intermediate results of each step in the pipeline, you can
call |pipeline_results_get|::

  for res in pipe.results.get(block=True):
    ...


Error Reporting
---------------

Reporting errors with Rollbar
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Rollbar_ provides an easy-to-use Python client.  Add it to your
project with pipenv_::

   $ pipenv install rollbar

Save the following middleware to a module inside your project:

.. code-block:: python

   import remoulade
   import rollbar

   class RollbarMiddleware(remoulade.Middleware):
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

   import remoulade

   class SentryMiddleware(remoulade.Middleware):
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

The `apistar_remoulade`_ library lets you use API Star dependency
injection with your Remoulade actors.

.. _apistar_remoulade: https://github.com/wiremind/apistar_remoulade
.. _API Star: https://github.com/encode/apistar


Django
^^^^^^

Check out the `django_remoulade`_ project if you want to use Remoulade
with Django_.  The `django_remoulade_example`_ repo is an example app
build with Django and Remoulade.

.. _django_remoulade: https://github.com/wiremind/django_remoulade
.. _django_remoulade_example: https://github.com/wiremind/django_remoulade_example
.. _django: https://djangoproject.com


Flask
^^^^^

The `flask_remoulade_example`_ repo is an example app built with Flask_
and Remoulade.

.. _flask_remoulade_example: https://github.com/wiremind/flask_remoulade_example
.. _flask: http://flask.pocoo.org


Operations
----------

Auto-discovering "tasks" modules with bash
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Remoulade doesn't attempt to auto-discover tasks modules.  Assuming you
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

   pipenv run remoulade-gevent $all_modules --watch . --watch-use-polling

Retrying connection errors on startup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Remoulade does not retry connection errors that occur on worker
startup.  It does, however, return a specific exit code (``3``) when
that happens.  Using that, you can build a wrapper script around it if
you need to retry with backoff when connection errors happen during
startup (eg. in Docker):

.. code-block:: bash

   #!/usr/bin/env bash

   delay=1
   while true; do
     remoulade $@
     if [ $? -eq 3 ]; then
       echo "Connection error encountered on startup. Retrying in $delay second(s)..."
       sleep $delay
       delay=$((delay * 2))
     else
       exit $?
     fi
   done

Binding Worker Groups to Queues
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, Remoulade workers consume all declared queues, but it's
common to want to bind worker groups to specific queues in order to
have better control over throughput.  For example, given the following
actors::

   @remoulade.actor
   def very_slow():
     ...

   @remoulade.actor(queue_name="ui-blocking")
   def very_important():
     ...

You may want to run one group of workers that only processes messages
on the ``default`` queue and another that only processes messages off
of the ``ui-blocking`` queue.  To do that, you have to pass each group
the appropriate queue on the command line:

.. code-block:: bash

   # Only consume the "default" queue
   $ remoulade an_app --queues default

   # Only consume the "ui-blocking" queue
   $ remoulade an_app --queues ui-blocking

Messages sent to ``very_slow`` will always be delievered to those
workers that consume the ``default`` queue and messages sent to
``very_important`` will always be delievered to the ones that consume
the ``ui-blocking`` queue.

Rate Limiting
-------------

Rate limiting work
^^^^^^^^^^^^^^^^^^

You can use Remoulade's |RateLimiters| to constrain actor concurrency.

.. code-block:: python

   import remoulade
   import time

   from remoulade.rate_limits import ConcurrentRateLimiter
   from remoulade.rate_limits.backends import RedisBackend

   backend = RedisBackend()
   DISTRIBUTED_MUTEX = ConcurrentRateLimiter(backend, "distributed-mutex", limit=1)

   @remoulade.actor
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

You can use Remoulade's result backends to store and retrieve message
return values.  To enable result storage, you need to instantiate and
add the |Results| middleware to your broker.

.. code-block:: python

   import remoulade

   from remoulade.brokers.rabbitmq import RabbitmqBroker
   from remoulade.results.backends import RedisBackend
   from remoulade.results import Results

   result_backend = RedisBackend()
   broker = RabbitmqBroker()
   broker.add_middleware(Results(backend=result_backend))
   remoulade.set_broker(broker)

   @remoulade.actor(store_results=True)
   def add(x, y):
     return x + y

   broker.declare_actor(add)

   if __name__ == "__main__":
     message = add.send(1, 2)
     print(message.result.get(block=True))

Getting a result raises |ResultMissing| when a result hasn't been
stored yet or if it has already expired (results expire after 10
minutes by default).  When the ``block`` parameter is ``True``,
|ResultTimeout| is raised instead. When the ``forget`` parameter
is ``True`` the result will be deleted from the backend when retrieved.

Result
^^^^^^
.. code-block:: python

   import remoulade

   from remoulade.brokers.rabbitmq import RabbitmqBroker
   from remoulade.results.backends import RedisBackend
   from remoulade.results import Results
   from remoulade.message_result import MessageResult

   result_backend = RedisBackend()
   broker = RabbitmqBroker()
   broker.add_middleware(Results(backend=result_backend))
   remoulade.set_broker(broker)

   @remoulade.actor(store_results=True)
   def add(x, y):
     return x + y

   broker.declare_actor(add)

   if __name__ == "__main__":
     message = add.send(1, 2)
     result = Result(message_id=message.message_id)
     print(result.get(block=True))


The property result of |Message| return a |Result| instance which can be used to get the result.
But you can also create a |Result| from a message_id and access to the result the same way.

Scheduling
----------

Scheduling messages
^^^^^^^^^^^^^^^^^^^

APScheduler_ is the recommended scheduler to use with Remoulade:

.. code-block:: python

   import remoulade
   import sys

   from apscheduler.schedulers.blocking import BlockingScheduler
   from apscheduler.triggers.cron import CronTrigger
   from datetime import datetime

   @remoulade.actor
   def print_current_date():
     print(datetime.now())

   if __name__ == "__main__":
     scheduler = BlockingScheduler()
     scheduler.add_job(
       print_current_date.send,
       CronTrigger.from_crontab("* * * * *"),
     )
     try:
       scheduler.start()
     except KeyboardInterrupt:
       scheduler.shutdown()

.. _APScheduler: https://apscheduler.readthedocs.io


Optimizing
----------

Prefetch Limits
^^^^^^^^^^^^^^^

The prefetch count is the number of message a worker can reserve for itself
(the limit of unacknowledged message it can get from RabbitMQ).

The prefetch count is set by multiplying the prefetch_multiplier with the number
of worker threads (default: 2)

If you have many actors with a long duration you want the multiplier value to be one,
it’ll only reserve one task per worker process at a time.

But if you have short actors, you may want to increase this multiplier to reduce I/O.

.. code-block:: bash

    remoulade package --prefetch-multiplier 1
