# Contributing

First off, thank you for considering to contribute!
There are several ways to contribute to Dramatiq,
even small things like reporting bugs help us out.

Please read and follow the following guidelines if 
you would like to contribute to Dramatiq.

## In General

Our contribution guidelines are written with the following goals in mind:

* Encourage respectful human interactions and contributions.
* Make Dramatiq a stable, reliable, library to work with.

## Feature Requests

We consider Dramatiq to be mostly feature-complete, and try to avoid adding new features 
where possible.

**Pull Requests opened for new features that haven't been discussed with a maintainer 
beforehand, are likely to be closed.**

Dramatiq has been designed to be extensible and pluggable by using custom classes.
For example, custom Middleware classes can add new functionality, and custom Broker 
and ResultBackend classes can make Dramatiq work with different backend services. 

Rather than adding new features to Dramatiq, see if you can achieve your desired 
functionality with a custom class.
If you need help with this, feel free to [start a discussion][discussion board].

If achieving your functionality is impossible with a custom class, or you *really* 
think it belongs in Dramatiq, then [start a discussion][discussion board] and describe 
what functionality you need.

## Bug Reports

[Opening a bug report][new bug report] (or adding to an existing report) is always 
recommended for any issues you have with Dramatiq.

This gives a maintainer the opportunity to discuss the issue with you, confirm if it is
actually a bug, and gauge its impact, before any fix is written.

**Pull Requests opened for bugs that haven't been discussed with a maintainer 
beforehand, may be closed.**

When opening a bug report make sure you include the full stack trace and that you list 
all pertinent information (operating system, message broker, Python implementation) as 
part of the issue description.
Please include a minimal, reproducible test case with every bug report.

Filling in the GitHub Bug Report template is the best way to ensure you have provided all 
this information.

## Contributing Code

As above, **Pull Requests opened without a discussion with a maintainer beforehand,
may be closed.** If you don't want to risk wasting your time, have a discussion first.

By submitting contributions, you disavow any rights or claims to any
changes submitted to the Dramatiq project and assign the copyright of
those changes to CLEARTYPE SRL.  If you cannot or do not want to
reassign those rights, you shouldn't submit a PR.  Instead, you should
open an issue and let someone else do that work.

### Local Development

To set up a development environment, it is recommended to:

1. Clone the repository (or your fork of it).
2. Create and active a virtual environment.
3. Install dramatiq in editable mode with all optional extras: `pip install -e ".[all]"`.
4. Install the development dependencies `pip install --group dev`.

### Commits

* Write an informative commit message.
* **Do not list any LLM/AI tools in the commit authors.** If you aren't willing to claim
  100% authorship of the commit, then we aren't interested in reviewing it.
* Don't worry if your commit history is messy, we can do a squash-merge in that case.
* On the other hand, if you have written a nice clean commit history, we can do a
  regular merge-commit merge to maintain it.

### Pull Requests

We are happy to give feedback and help you improve your human-written Pull Request.
It doesn't need to be perfect first time!
However, we are not interested in engaging with Pull Requests opened by automated tools.

*Pull Requests that we suspect are opened by automated tools, will be closed.*

Before opening a Pull Request;

* Make sure any code changes are covered by tests.
* Run [black], [isort] and [flake8] on any modified files.
* Run [mypy] to check type correctness.
* If this is your first contribution, add yourself to the [CONTRIBUTORS] file.

Run the test suite with [pytest]. The tests require running [RabbitMQ],
[Redis] and [Memcached] servers.

There is a `tox.ini` file if you wish to run the whole test matrix with [tox],
but generally it is ok to let GitHub CI do that.

#### Automated Review Tools

Do not trigger reviews by automated tools in the main Dramatiq repository.
If you wish to use these tools, do so in your own fork.


[CONTRIBUTORS]: https://github.com/Bogdanp/dramatiq/blob/master/CONTRIBUTORS.md
[RabbitMQ]: https://www.rabbitmq.com/
[Redis]: https://redis.io
[Memcached]: https://memcached.org/
[isort]: https://github.com/timothycrosley/isort
[black]: https://github.com/psf/black
[flake8]: https://flake8.pycqa.org/en/latest/
[mypy]: https://mypy.readthedocs.io/en/stable/getting_started.html
[pytest]: https://docs.pytest.org/en/stable/index.html
[tox]: https://tox.wiki/en/stable/
[discussion board]: https://groups.io/g/dramatiq-users
[new bug report]: https://github.com/Bogdanp/dramatiq/issues/new?template=bug_report.md
