.. include:: global.rst

User Guide
==========

To follow along with this guide you'll need to install and run RabbitMQ_
and then set up a new `virtual environment`_ in which you'll have
to install Dramatiq and Requests_::

  $ pip install dramatiq[rabbitmq, watch] requests

.. _requests: http://docs.python-requests.org
.. _virtual environment: http://docs.python-guide.org/en/latest/starting/install3/osx/#virtual-environments


Actors
------

As a quick and dirty example of a task that's worth processing in the
background, let's write a function that counts the "words" at a
particular URL:

.. code-block:: python
   :caption: count_words.py

   import requests

   def count_words(url):
     response = requests.get(url)
     count = len(response.text.split(" "))
     print(f"There are {count} words at {url!r}.")

There's not a ton going on here.  We just grab the response content at
that URL and print out how many space-separated chunks there are in
that response.  Sure enough, running this in the interactive
interpreter yields about what we expect::

  >>> from count_words import count_words
  >>> count_words("http://example.com")
  There are 338 words at 'http://example.com'.

To turn this into a function that can be processed asynchronously
using Dramatiq, all we have to do is decorate it with |actor|:

.. code-block:: python
   :caption: count_words.py
   :emphasize-lines: 1, 4

   import dramatiq
   import requests

   @dramatiq.actor
   def count_words(url):
     response = requests.get(url)
     count = len(response.text.split(" "))
     print(f"There are {count} words at {url!r}.")

Like before, if we call the function in the interactive interpreter,
it will run synchronously and we'll get the same result out::

  >>> count_words("http://example.com")
  There are 338 words at 'http://example.com'.

What's changed is we're now able to tell the function to run
asynchronously by calling its |send| method::

  >>> count_words.send("http://example.com")
  Message(
    queue_name='default',
    actor_name='count_words',
    args=('http://example.com',), kwargs={}, options={},
    message_id='8cdcae57-af36-40ba-9616-849a336a4316',
    message_timestamp=1498557015410)

Doing so immediately enqueues a message (via our local RabbitMQ
server) that can be processed asynchronously but *doesn't actually run
the function*.  In order to run it, we'll have to boot up a Dramatiq
worker.

.. note::
   Because all messages have to be sent over the network, any
   arguments you send to an actor must be JSON-encodable.


Workers
-------

Dramatiq comes with a command line utility called, predictably,
``dramatiq``.  This utility is able to spin up multiple concurrent
worker processes that pop messages off the queue and send them to
actor functions for execution.

To spawn workers for our ``count_words.py`` example, run the following
command in a new terminal window::

  $ env PYTHONPATH=. dramatiq count_words

This will spin up as many processes as there are CPU cores on your
machine with 8 worker threads per process.  Run ``dramatiq -h`` if you
want to see a list of the available command line flags.

As soon as you run that command you'll see log output along these
lines::

  [2017-06-27 13:03:09,675] [PID 13047] [MainThread] [dramatiq.MainProcess] [INFO] Dramatiq '0.5.0' is booting up.
  [2017-06-27 13:03:09,817] [PID 13051] [MainThread] [dramatiq.WorkerProcess(1)] [INFO] Worker process is ready for action.
  [2017-06-27 13:03:09,818] [PID 13052] [MainThread] [dramatiq.WorkerProcess(2)] [INFO] Worker process is ready for action.
  [2017-06-27 13:03:09,818] [PID 13050] [MainThread] [dramatiq.WorkerProcess(0)] [INFO] Worker process is ready for action.
  [2017-06-27 13:03:09,819] [PID 13053] [MainThread] [dramatiq.WorkerProcess(3)] [INFO] Worker process is ready for action.
  [2017-06-27 13:03:09,821] [PID 13054] [MainThread] [dramatiq.WorkerProcess(4)] [INFO] Worker process is ready for action.
  [2017-06-27 13:03:09,829] [PID 13056] [MainThread] [dramatiq.WorkerProcess(6)] [INFO] Worker process is ready for action.
  [2017-06-27 13:03:09,832] [PID 13055] [MainThread] [dramatiq.WorkerProcess(5)] [INFO] Worker process is ready for action.
  [2017-06-27 13:03:09,833] [PID 13057] [MainThread] [dramatiq.WorkerProcess(7)] [INFO] Worker process is ready for action.
  There are 338 words at 'http://example.com'.

If you open your Python interpreter back up and send the actor some
more URLs to process::

  >>> urls = [
  ...   "https://news.ycombinator.com",
  ...   "https://xkcd.com",
  ...   "https://rabbitmq.com",
  ... ]
  >>> [count_words.send(url) for url in urls]
  [Message(queue_name='default', actor_name='count_words', args=('https://news.ycombinator.com',), kwargs={}, options={}, message_id='a99a5b2d-d2da-407b-be55-f2925266e216', message_timestamp=1498557998218),
   Message(queue_name='default', actor_name='count_words', args=('https://xkcd.com',), kwargs={}, options={}, message_id='0ec93dcb-2f9f-414f-99ec-7035e3b1ac5a', message_timestamp=1498557998218),
   Message(queue_name='default', actor_name='count_words', args=('https://rabbitmq.com',), kwargs={}, options={}, message_id='d3dd9799-1ea5-4b00-a70b-2cd6f6f634ed', message_timestamp=1498557998218)]

and then switch back to the worker terminal, you'll see three new
lines::

  There are 467 words at 'https://xkcd.com'.
  There are 3962 words at 'https://rabbitmq.com'.
  There are 3589 words at 'https://news.ycombinator.com'.

At this point, you're probably wondering what happens if you send the
actor an invalid URL.  Let's try it::

  >>> count_words.send("foo")


Error Handling
--------------

Dramatiq strives for at-least-once message delivery and assumes all
actors are idempotent.  When an exception occurs while a message is
being processed, Dramatiq automatically enqueues a retry for that
message with exponential backoff.

That last message we sent will cause something along these lines to be
printed in your worker process::

  [2017-06-27 13:11:22,059] [PID 13053] [Thread-8] [dramatiq.worker.WorkerThread] [WARNING] Failed to process message count_words('foo') with unhandled exception.
  Traceback (most recent call last):
    ...
  requests.exceptions.MissingSchema: Invalid URL 'foo': No schema supplied. Perhaps you meant http://foo?
  [2017-06-27 13:11:22,062] [PID 13053] [Thread-8] [dramatiq.middleware.retries.Retries] [INFO] Retrying message 'a53a5a7d-74e1-48ae-a5a8-0b72af2a8708' as 'cc6a9b6d-873d-4555-a5d1-98d816775049' in 8104 milliseconds.

Dramatiq will keep retrying the message with longer and longer delays
in between runs until we fix our code or for up to about 30 days from
when it was first enqueued.

Change ``count_words`` to catch the missing schema error::

   @dramatiq.actor
   def count_words(url):
     try:
       response = requests.get(url)
       count = len(response.text.split(" "))
       print(f"There are {count} words at {url!r}.")
     except requests.exceptions.MissingSchema:
       print(f"Message dropped due to invalid url: {url!r}")

Then send ``SIGHUP`` to the main worker process to make the workers
pick up the source code changes::

  $ kill -s HUP 13047

Substitute the process ID of your own main process for ``13047``.  You
can find the PID by looking at the log lines from the worker starting
up.  Look for lines containing the string ``[dramatiq.MainProcess]``.

The next time your message is retried you should see::

  Message dropped due to invalid url: 'foo'


Code Reloading
--------------

Sending ``SIGHUP`` to the workers every time you make a change is
going to get old quick.  Instead, you can run the command line utility
with the ``--watch`` flag pointing to the folder it should watch for
source code changes.  It'll reload the workers whenever Python files
under that folder or any of its sub-folders change::

  $ env PYTHONPATH=. dramatiq count_words --watch .

.. warning::
   While this is a great feature to use when developing your code,
   avoid using it in production!


Message Retries
---------------

As mentioned in the error handling section, Dramatiq automatically
retries failures with exponential backoff.

You can specify how failures should be retried on a per-actor basis.
For example, if you want to limit the maximum number of retries for
``count_words`` you can pass the ``max_retries`` keyword argument to
|actor|::

  @dramatiq.actor(max_retries=3)
  def count_words(url):
    ...

The following retry options are configurable on a per-actor basis:

===============  ============  ====================================================================================================================
Option           Default       Description
===============  ============  ====================================================================================================================
``max_retries``  ``20``        The maximum number of times a message should be retried.  ``None`` means the message should be retried indefinitely.
``min_backoff``  15 seconds    The minimum number of milliseconds of backoff to apply between retries.  Must be greater than 100 milliseconds.
``max_backoff``  7 days        The maximum number of milliseconds of backoff to apply between retries.  Must be less than or equal to 7 days.
===============  ============  ====================================================================================================================


Message Age Limits
------------------

Instead of limiting the number of times messages can be retried, you
might want to expire old messages.  You can specify the ``max_age`` of
messages (given in milliseconds) on a per-actor basis::

  @dramatiq.actor(max_age=3600000)
  def count_words(url):
    ...

Dead Letters
^^^^^^^^^^^^

Once a message has exceeded its retry or age limits, it gets moved to
the dead letter queue where it's kept for up to 7 days and then
automatically dropped from the message broker.  From here, you can
manually inspect the message and decide whether or not it should be
put back on the queue.


Message Time Limits
-------------------

In ``count_words``, we didn't set an explicit timeout for the outbound
request which means that it can take a very long time to complete if
the server we're requesting is timing out.  Dramatiq has a default
actor time limit of 10 minutes, which means that any actor running for
longer than 10 minutes is killed with a |TimeLimitExceeded| error.

You can control these time limits at the individual actor level by
specifying the ``time_limit`` (in milliseconds) of each one::

  @dramatiq.actor(time_limit=60000)
  def count_words(url):
    ...

.. note::
   While this will keep our actor from running forever, remember that
   you should take care to always specify a timeout for the request
   itself, and this is **not** a good way to handle request timeouts
   in production code.

.. warning::
   Time limits are best-effort.  They cannot cancel system calls or
   any function that doesn't currently hold the GIL under CPython.


Handling Time Limits
^^^^^^^^^^^^^^^^^^^^

If you want to gracefully handle time limits within an actor, you can
wrap its source code in a try block and catch |TimeLimitExceeded|::

  from dramatiq.middleware import TimeLimitExceeded

  @dramatiq.actor(time_limit=1000)
  def long_running():
    try:
      setup_missiles()
      time.sleep(2)
      launch_missiles()    # <- this will not run
    except TimeLimitExceeded:
      teardown_missiles()  # <- this will run


Scheduling Messages
-------------------

You can schedule messages to run up to 7 days into the future by
calling |send_with_options| on actors and providing a ``delay`` (in
milliseconds)::

  >>> count_words.send_with_options(args=("https://example.com",), delay=10000)
  Message(
    queue_name='default',
    actor_name='count_words',
    args=('https://example.com',), kwargs={},
    options={'eta': 1498560453548},
    message_id='7387dc76-8ebe-426e-aec1-db34c236563c',
    message_timestamp=1498560443548)

Keep in mind that *your message broker is not a database*.  Scheduled
messages should represent a small subset of all your messages.


Prioritizing Messages
---------------------

Say your app has some actors that are higher priority than others: for
example, actors that affect your UI and make users wait, or are
otherwise user-facing, versus actors that aren't.  When choosing
between two concurrent messages to run, Dramatiq will run the Message
that belongs to the actor with the highest priority.

You can set an Actor's priority via the ``priority`` keyword argument::

  @dramatiq.actor(priority=0)  # 0 is the default
  def generate_report(user_id):
    ...

  @dramatiq.actor(priority=10)
  def sync_order_to_warehouse(order_id):
    ...

That way if both ``generate_report`` and ``sync_order_to_warehouse``
are scheduled to run at the same time but there's only capacity to run
one of them, ``generate_report`` will always run *first*.

Although all positive integers represent valid priorities, if you're
going to use this feature, I'd recommend setting up constants for the
various priorities you plan to use::

  PRIO_LO = 100
  PRIO_MED = 50
  PRIO_HI = 0

.. important::
   The lower the numeric value, the higher priority!  If you need a
   mnemonic to remember this, think of having a ticket with a number
   on it handed to you while waiting in line, perhaps at a government
   institution or deli counter.


Message Brokers
---------------

Dramatiq abstracts over the notion of a message broker and currently
supports both RabbitMQ and Redis out of the box.  By default, it'll
set up a RabbitMQ broker instance pointing at the local host.

RabbitMQ Broker
^^^^^^^^^^^^^^^

To configure the RabbitMQ host, instantiate a |RabbitmqBroker| and set
it as the global broker as early as possible during your program's
execution::

  import dramatiq
  import pika

  from dramatiq.brokers.rabbitmq import RabbitmqBroker

  conn_parameters = pika.ConnectionParameters(
    host="rabbitmq",
    heartbeat_interval=0,
  )
  rabbitmq_broker = RabbitmqBroker(parameters=conn_parameters)
  dramatiq.set_broker(rabbitmq_broker)

Make sure to disable heartbeats when defining your own connection
parameters by passing them ``heartbeat_interval=0`` since pika's
``BlockingConnection`` does not handle heartbeats.

Redis Broker
^^^^^^^^^^^^

To use Dramatiq with the Redis broker, create an instance of it and
set it as the global broker as early as possible during your program’s
execution::

  import dramatiq

  from dramatiq.brokers.redis import RedisBroker

  redis_broker = RedisBroker(host="redis", port=6537)
  dramatiq.set_broker(redis_broker)


Unit Testing
------------

Dramatiq provides a |StubBroker| that can be used in unit tests so you
don't have to have a running RabbitMQ or Redis instance in order to
run your tests.  My recommendation is to use it in conjunction with
`pytest fixtures`_:

.. code-block:: python
   :caption: broker.py

   import os

   from dramatiq.brokers.rabbitmq import RabbitmqBroker
   from dramatiq.brokers.stub import StubBroker

   if os.getenv("UNIT_TESTS") == "1":
       broker = StubBroker()
       broker.emit_after("process_boot")
   else:
       broker = RabbitmqBroker()

.. code-block:: python
   :caption: conftest.py

   import dramatiq
   import pytest

   from yourapp import broker

   @pytest.fixture(scope="global")
   def stub_broker():
     return broker

   @pytest.fixture()
   def stub_worker():
     worker = Worker(broker, worker_timeout=100)
     worker.start()
     yield worker
     worker.stop()

Then you can inject and use those fixtures in your tests::

  def test_count_words(stub_broker, stub_worker):
    count_words.send("http://example.com")
    stub_broker.join(count_words.queue_name)
    stub_worker.join()

Because all actors are callable, you can of course also unit test them
synchronously by calling them as you would normal functions.


.. _pytest fixtures: https://docs.pytest.org/en/latest/fixture.html
