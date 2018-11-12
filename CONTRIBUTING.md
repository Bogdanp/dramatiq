# Contributing

## Code

[Start a discussion] before attempting to make a contribution.  Any
contribution that doesn't fit my design goals for the project will be
rejected so it's always better to start a discussion first!

By submitting contributions, you disavow any rights or claims to any
changes submitted to the Remoulade project and assign the copyright of
those changes to WIREMIND SAS.  If you cannot or do not want to
reassign those rights, you shouldn't submit a PR.  Instead, you should
open an issue and let someone else do that work.

### Pull Requests

* Make sure any code changes are covered by tests.
* Run [isort] on any modified files.
* If this is your first contribution, add yourself to the [CONTRIBUTORS] file.
* If your branch is behind master, [rebase] on top of it.

Run the test suite with `tox`.  The tests require running [RabbitMQ] and [Redis].

[CONTRIBUTORS]: https://github.com/wiremind/remoulade/blob/master/CONTRIBUTORS.md
[RabbitMQ]: https://www.rabbitmq.com/
[Redis]: https://redis.io
[isort]: https://github.com/timothycrosley/isort
[rebase]: https://github.com/edx/edx-platform/wiki/How-to-Rebase-a-Pull-Request


## Issues

When you open an issue make sure you include the full stack trace and
that you list all pertinent information (operating system, message
broker, Python implementation) as part of the issue description.

Please include a minimal, reproducible test case with every bug
report.  If the issue is actually a question, consider asking it on
Stack Overflow first.
