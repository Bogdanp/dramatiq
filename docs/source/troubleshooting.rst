.. include:: global.rst

Troubleshooting
===============

This part of the documentation contains solutions to common problems
you may encounter in the real world.


``FileNotFoundError`` when Enqueueing
-------------------------------------

Dramatiq operations on builtin brokers are thread-safe, however they
are not *process* safe so, if you use a pre-forking web server that
forks *after* loading all of your code, then it's likely you'll run
into issues enqueueing messages.  That is because fork has
copy-on-write semantics on most systems so any file descriptors open
before forking will be shared between all of the processes.

``gunicorn`` Workaround
^^^^^^^^^^^^^^^^^^^^^^^

This problem should not occur under gunicorn_ since it loads the
application after forking by default.

.. _gunicorn: https://gunicorn.org/

``uwsgi`` Workaround
^^^^^^^^^^^^^^^^^^^^

To work around this problem in uwsgi_, you have to turn on `lazy apps
mode`_.  This will ensure that all your app code is loaded after each
worker process is forked.  The tradeoff you make by turning on this
option is your application will use slightly more memory.

.. _uwsgi: https://uwsgi-docs.readthedocs.io/en/latest
.. _lazy apps mode: https://uwsgi-docs.readthedocs.io/en/latest/Options.html#lazy-apps


Integration Tests Hang
----------------------

During integration tests, actors are executed in a separate thread
from the main thread that is running your code, just like they would
be in the real world.  In that sense, the |StubBroker| is great
because it helps you simulate real-world execution conditions when
you're testing your controller code.

The main drawback to this approach is that -- because the actors are
run in a separate thread -- your testing code has no way of knowing
when an actor fails so, often, your tests may hang waiting for a
message to be processed.  An easy way to notice when these types of
issues occur, is to turn on logging for your tests.  If you use
pytest_, then you can easily do this from the command line using the
``--log-cli-level`` flag::

  $ py.test --log-cli-level=warning

You can also pass ``fail_fast=True`` as a parameter to |StubBroker_join|
in order to make it reraise whatever exception caused the actor to
fail in the main thread.  Note, however, that the actor is only
considered to fail once all of its retries have been used up; meaning
that unless you specify custom retry limits for the actors or for your
tests as a whole (by configuring the |Retries| middleware), then each
actor will retry for up to about 30 days before exhausting its
available retries!

.. _pytest: https://docs.pytest.org/en/latest/
