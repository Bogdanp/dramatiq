.. include:: global.rst

User Guide
==========

To get started, run ``rabbitmq-server`` in a terminal window and fire
up your favorite code editor.  For the purposes of this guide, I'll
assume you've created a new virtualenv_ and have installed Dramatiq
with RabbitMQ support as well as the requests_ library.

.. _requests: http://docs.python-requests.org/en/latest/
.. _virtualenv: http://docs.python-guide.org/en/latest/starting/installation/


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

As before, if we call the function in the interactive interpreter, the
function will run synchronusly and we'll get the same result out::

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

Doing so immediately enqueues a message that can be processed
asynchronously but *doesn't* run the function in the current process.
In order to run it, we'll have to boot up a Dramatiq worker.

.. note::
   Because all messages have to be sent over the network, any
   parameter you send to an actor must be JSON-encodable.


Workers
-------

Dramatiq comes with a CLI utility called, predictably, ``dramatiq``.
This utility is able to spin up multiple concurrent worker processes
that pop messages off the queue and send them to actors for execution.

To spawn workers for our ``count_words.py`` example, all we have to do
is::

  $ env PYTHONPATH=. dramatiq count_words

This will spin up as many processes as there are CPU cores on your
machine with 8 worker threads per process.  What this means is that if
you have an 8 core machine, Dramatiq will spawn 64 worker threads
making it so you can process up to 64 messages concurrently on that
machine.

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

If you open your python interpreter back up and send the actor some
more URLs to process

::

  >>> urls = [
  ...   "https://news.ycombinator.com",
  ...   "https://xkcd.com",
  ...   "https://rabbitmq.com",
  ... ]
  >>> [count_words.send(url) for url in urls]
  [Message(queue_name='default', actor_name='count_words', args=('https://news.ycombinator.com',), kwargs={}, options={}, message_id='a99a5b2d-d2da-407b-be55-f2925266e216', message_timestamp=1498557998218),
   Message(queue_name='default', actor_name='count_words', args=('https://xkcd.com',), kwargs={}, options={}, message_id='0ec93dcb-2f9f-414f-99ec-7035e3b1ac5a', message_timestamp=1498557998218),
   Message(queue_name='default', actor_name='count_words', args=('https://rabbitmq.com',), kwargs={}, options={}, message_id='d3dd9799-1ea5-4b00-a70b-2cd6f6f634ed', message_timestamp=1498557998218)]

and then switch back to the worker terminal, you'll see three new lines::

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
in between runs until we fix our code.  Lets do that: change
``count_words`` to catch the missing schema error::

   @dramatiq.actor
   def count_words(url):
     try:
       response = requests.get(url)
       count = len(response.text.split(" "))
       print(f"There are {count} words at {url!r}.")
     except requests.exceptions.MissingSchema:
       print(f"Message dropped due to invalid url: {url!r}")

To make the workers pick up the source code changes, send ``SIGHUP``
to the main worker process::

  $ kill -s HUP 13047

The next time your message is run you should see::

  Message dropped due to invalid url: 'foo'


Code Reloading
--------------

Sending ``SIGHUP`` to the workers every time you make a change is
going to get old quick.  Instead, you can run the CLI utility with the
``--watch`` flag pointing to the folder it should watch for source
code changes.  It'll reload the workers whenever Python files under
that folder or any of its subfolders change::

  $ env PYTHONPATH=. dramatiq count_words --watch .

.. warning::
   While this is a great feature to use while developing your code, avoid
   using it in production!


Message Retries
---------------

As mentioned in the error handling section, Dramatiq automatically
retries failing messages with exponential backoff.  You can specify
how messages should be retried on a per-actor basis.  For example, if
we wanted to limit the max number of retries for ``count_words`` we'd
specify the ``max_retries`` keyword argument to |actor|::

  @dramatiq.actor(max_retries=3)
  def count_words(url):
    ...

The following retry options are configurable on a per-actor basis:

===============  ============  ====================================================================================================================
Option           Default       Description
===============  ============  ====================================================================================================================
``max_retries``  ``None``      The maximum number of times a message should be retried.  ``None`` means the message should be retried indefinitely.
``min_backoff``  15 seconds    The minimum number of milliseconds of backoff to apply between retries.  Must be greater than 100 milliseconds.
``max_backoff``  7 days        The maximum number of milliseconds of backoff to apply between retries.  Must be less than or equal to 7 days.
===============  ============  ====================================================================================================================


Message Age Limits
------------------

Instead of limiting the number of times messages can be retried, you
might want to expire old messages.  You can specify the ``max_age`` of
messages on a per-actor basis::

  @dramatiq.actor(max_age=3600000)
  def count_words(url):
    ...


Message Time Limits
-------------------

In ``count_words``, we didn't set a timeout for the outbound request
which means that it can take a very long time to complete if the
server we're requesting is timing out.  Dramatiq has a default actor
time limit of 10 minutes, which means that any actor running for
longer than 10 minutes is killed with a |TimeLimitExceeded| error.

You can control these time limits at the individual actor level by
specifying the ``time_limit`` of each one::

  @dramatiq.actor(time_limit=60000)
  def count_words(url):
    ...

.. note::
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
calling |send_with_options| on actors and providing a ``delay``::

  >>> count_words.send_with_options(args=("https://example.com",), delay=10000)
  Message(
    queue_name='default',
    actor_name='count_words',
    args=('https://example.com',), kwargs={},
    options={'eta': 1498560453548},
    message_id='7387dc76-8ebe-426e-aec1-db34c236563c',
    message_timestamp=1498560443548)

Keep in mind that *your message broker is not a database*.  Scheduled
messages should represent a small subset of your total number of
messages.


Prioritizing Messages
---------------------

Say your app has some actors that are higher priority than others:
eg. actors that affect the UI/are somehow user-facing versus actors
that aren't.  When choosing between two concurrent messages to run,
Dramatiq will run the Message whose actor has a lower numeric
priority.

You can set an Actor's priority via the ``priority`` keyword argument::

  @dramatiq.actor(priority=0)  # 0 is the default
  def ui_facing():
    ...

  @dramatiq.actor(priority=10)
  def background():
    ...


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
parameters by passing them ``heartbeat_interval=0`` since *pika's*
``BlockingConnection`` does not handle heartbeats.

Redis Broker
^^^^^^^^^^^^

To use Dramatiq with the Redis broker, create an instance of it and
set it as the global broker as early during your program's execution
as possible::

  import dramatiq

  from dramatiq.brokers.redis import RedisBroker

  redis_broker = RedisBroker(host="redis", port=6537)
  dramatiq.set_broker(redis_broker)


Unit Testing
------------

Dramatiq provides a |StubBroker| that can be used in unit tests so you
don't have to have a running RabbitMQ or Redis instance in order to
run your tests.  My recommendation is to use it in conjunction with
`pytest fixtures`_::

  import dramatiq
  import pytest

  from dramatiq.brokers.stub import StubBroker

  @pytest.fixture()
  def stub_broker():
    broker = StubBroker()
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)
    yield broker
    broker.close()

  @pytest.fixture()
  def stub_worker(stub_broker):
    worker = Worker(stub_broker, worker_timeout=100)
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
