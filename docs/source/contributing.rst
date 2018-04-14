.. include:: global.rst

Contributing
============

Code
----

Open an issue before attempting to make a contribution.  Any
contribution that doesn't fit my design goals for the project will be
rejected so it's always better to start a discussion first!

By submitting contributions, you disavow any rights or claims to any
changes submitted to the Dramatiq project and assign the copyright of
those changes to CLEARTYPE SRL.  If you cannot or do not want to
reassign those rights, you shouldn't submit a PR.  Instead, you should
open an issue and let someone else do that work.

Pull Requests
^^^^^^^^^^^^^

* Add at least one test for any code change.
* If this is your first contribution, add yourself to the
  CONTRIBUTORS_ file.
* If your branch is behind master, rebase_ on top of it.

Run the test suite with ``tox``.  The tests require running RabbitMQ_,
Redis_ and Memcached_ servers.

.. _rebase: https://github.com/edx/edx-platform/wiki/How-to-Rebase-a-Pull-Request
.. _CONTRIBUTORS: https://github.com/Bogdanp/dramatiq/blob/master/CONTRIBUTORS.md


Issues
------

When you open an issue make sure you include the full stack trace and
that you list all pertinent information (operating system, message
broker, Python implementation) as part of the issue description.
Please include a minimal, reproducible test case with every bug
report.  If the issue is actually a question, consider asking it on
the forum_ or Stack Overflow first.

.. _forum: https://discuss.dramatiq.io
