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
option is your application will use slighly more memory.

.. _uwsgi: https://uwsgi-docs.readthedocs.io/en/latest
.. _lazy apps mode: https://uwsgi-docs.readthedocs.io/en/latest/Options.html#lazy-apps
