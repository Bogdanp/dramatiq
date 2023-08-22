.. include:: global.rst

Cookbook
========

This part of the docs contains recipes for various things you might
want to do using Dramatiq.  Each section will be light on prose and
code heavy, so if you have any questions about one of the recipes,
open an `issue on GitHub`_.

.. _issue on GitHub: https://github.com/Bogdanp/dramatiq/issues


Callbacks
---------

Dramatiq has built-in support for sending actors messages when other
actors succeed or fail.  The ``on_failure`` callback is called every
time an actor fails, even if the message is going to be retried.

.. code-block:: python

   import dramatiq


   @dramatiq.actor
   def identity(x):
       return x


   @dramatiq.actor
   def print_result(message_data, result):
       print(f"The result of message {message_data['message_id']} was {result}.")

   @dramatiq.actor
   def print_error(message_data, exception_data):
       print(f"Message {message_data['message_id']} failed:")
       print(f"  * type: {exception_data['type']}")
       print(f"  * message: {exception_data['message']!r}")


   if __name__ == "__main__":
       identity.send_with_options(
           args=(42,),
           on_failure=print_error,
           on_success=print_result,
       )


Composition
-----------

Dramatiq has built-in support for a couple high-level composition
constructs.  You can use these to combine generalized tasks that don't
know about one another into complex workflows.

In order to take advantage of group and pipeline result management
or to wait for a group or pipeline to finish, you need to enable
result storage and your actors need to store results.  Check out the
`Results`_ section for more information on result storage.

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

  for res in g.get_results(block=True, timeout=5_000):
      ...

Results are returned in the same order that the messages were added to
the group.

Pipelines
^^^^^^^^^

Actors can be chained together using the |pipeline| function.  For
example, if you have an actor that gets the text contents of a website
and one that counts the number of "words" in a piece of text:

.. code-block:: python

   @dramatiq.actor
   def get_uri_contents(uri):
       return requests.get(uri).text


   @dramatiq.actor
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
you can call |pipeline_get_result|::

  pipe.get_result(block=True, timeout=5_000)

To get the intermediate results of each step in the pipeline, you can
call |pipeline_get_results|::

  for res in pipe.get_results(block=True):
      ...


Error Reporting
---------------

Reporting errors with Rollbar
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Rollbar_ provides an easy-to-use Python client::

   $ pip install rollbar

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


.. _Rollbar: https://github.com/rollbar/pyrollbar#quick-start

Reporting errors with Sentry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use `sentry-dramatiq`_.

.. _sentry-dramatiq: https://pypi.org/project/sentry-dramatiq/


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

The `Flask-Dramatiq`_ extension integrates Dramatiq with Flask_.  It
includes support for configuration and the application factory
pattern.  `Flask-Melodramatiq`_ is very similar in scope, but tries to
stay as close as possible to the "native" Dramatiq API.

.. _Flask-Dramatiq: https://flask-dramatiq.readthedocs.io
.. _Flask-Melodramatiq: https://flask-melodramatiq.readthedocs.io
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

   dramatiq-gevent $all_modules --watch . --watch-use-polling

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

Binding Worker Groups to Queues
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, Dramatiq workers consume all declared queues, but it's
common to want to bind worker groups to specific queues in order to
have better control over throughput.  For example, given the following
actors::

   @dramatiq.actor
   def very_slow():
       ...


   @dramatiq.actor(queue_name="ui-blocking")
   def very_important():
       ...

You may want to run one group of workers that only processes messages
on the ``default`` queue and another that only processes messages off
of the ``ui-blocking`` queue.  To do that, you have to pass each group
the appropriate queue on the command line:

.. code-block:: bash

   # Only consume the "default" queue
   $ dramatiq an_app --queues default

   # Only consume the "ui-blocking" queue
   $ dramatiq an_app --queues ui-blocking

Messages sent to ``very_slow`` will always be delivered to those
workers that consume the ``default`` queue and messages sent to
``very_important`` will always be delivered to the ones that consume
the ``ui-blocking`` queue.

Rate Limiting
-------------

Rate limiting work
^^^^^^^^^^^^^^^^^^

You can use Dramatiq's |RateLimiters| to constrain actor concurrency.

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
an exception and relying on the built-in
:class:`Retries<dramatiq.middleware.Retries>` middleware to do the
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

You can use Dramatiq's result backends to store and retrieve message
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

When a message fails, getting a result raises |ResultFailure|.  When a
message is skipped via |SkipMessage|, ``None`` is stored as the
result.

Results expire, otherwise the result backend would eventually run out
of space.  The timeout for the results expiration is set on
`result_ttl` argument of |Results|, given in milliseconds, and the
default is 10 minutes.

.. code-block:: python

   # Results are valid only for one hour
   Results(backend=result_backend, result_ttl=3600*1000)

The result expiration can be also set per an actor:

.. code-block:: python

   # Add result expires in 30 seconds
   @dramatiq.actor(store_results=True, result_ttl=30*1000)
   def add(x, y):
       return x + y

Scheduling
----------

Scheduling messages
^^^^^^^^^^^^^^^^^^^

APScheduler_ is the recommended scheduler to use with Dramatiq:

.. code-block:: python

   import dramatiq
   import sys

   from apscheduler.schedulers.blocking import BlockingScheduler
   from apscheduler.triggers.cron import CronTrigger
   from datetime import datetime


   @dramatiq.actor
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


Aborting
--------

Aborting Messages
^^^^^^^^^^^^^^^^^

The `dramatiq-abort`_ package provides a middleware that can be used
to abort running actors by message id.  Here's how you might set it
up::

  import dramatiq
  import dramatiq_abort.backends
  from dramatiq_abort import Abortable, abort

  abortable = Abortable(
      backend=dramatiq_abort.backends.RedisBackend()
  )
  dramatiq.get_broker().add_middleware(abortable)

  @dramatiq.actor
  def a_long_running_task():
      ...

  message = a_long_running_task.send()
  abort(message.message_id)

.. _`dramatiq-abort`: https://flared.github.io/dramatiq-abort/
