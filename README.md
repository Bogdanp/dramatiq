<img src="https://dramatiq.io/_static/logo.png" align="right" width="131" />

# dramatiq

[![Build Status](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Factions-badge.atrox.dev%2Fbogdanp%2Fdramatiq%2Fbadge&style=flat)](https://actions-badge.atrox.dev/bogdanp/dramatiq/goto)
[![PyPI version](https://badge.fury.io/py/dramatiq.svg)](https://badge.fury.io/py/dramatiq)
[![Documentation](https://img.shields.io/badge/doc-latest-brightgreen.svg)](http://dramatiq.io)
[![Discourse](https://img.shields.io/badge/discuss-online-orange.svg)](https://reddit.com/r/dramatiq)

*A fast and reliable distributed task processing library for Python 3.*

<hr/>

**Changelog**: https://dramatiq.io/changelog.html <br/>
**Community**: https://reddit.com/r/dramatiq <br/>
**Documentation**: https://dramatiq.io <br/>
[**Support Dramatiq via Patreon**](https://patreon.com/popabogdanp) <br/>
[**Support Dramatiq via Tidelift**](https://tidelift.com/subscription/pkg/pypi-dramatiq?utm_source=pypi-dramatiq&utm_medium=referral&utm_campaign=readme)

<hr/>

## Installation

If you want to use it with [RabbitMQ]

    pip install 'dramatiq[rabbitmq, watch]'

or if you want to use it with [Redis]

    pip install 'dramatiq[redis, watch]'


## Supporting the Project

If you use and love Dramatiq and want to make sure it gets the love
and attention it deserves then you should consider supporting the
project.  There are three ways in which you can do this right now:

1. If you're a company that uses Dramatiq in production then you can
   get a [Tidelift] subscription.  Doing so will give you an easy
   route to supporting both Dramatiq and other open source projects
   that you depend on.
2. If you're an individual or a company that doesn't want to go
   through Tidelift then you can support the project via [Patreon].
3. If you're a company and neither option works for you and you would
   like to receive an invoice from me directly then email me at
   bogdan@defn.io and let's talk.

[Tidelift]: https://tidelift.com/subscription/pkg/pypi-dramatiq?utm_source=pypi-dramatiq&utm_medium=referral&utm_campaign=readme
[Patreon]: https://patreon.com/popabogdanp


## Quickstart

Make sure you've got [RabbitMQ] running, then create a new file called
`example.py`:

``` python
import dramatiq
import requests
import sys


@dramatiq.actor
def count_words(url):
    response = requests.get(url)
    count = len(response.text.split(" "))
    print(f"There are {count} words at {url!r}.")


if __name__ == "__main__":
    count_words.send(sys.argv[1])
```

In one terminal, run your workers:

    dramatiq example

In another, start enqueueing messages:

    python example.py http://example.com
    python example.py https://github.com
    python example.py https://news.ycombinator.com

Check out the [user guide] to learn more!


## License

dramatiq is licensed under the LGPL.  Please see [COPYING] and
[COPYING.LESSER] for licensing details.


[COPYING.LESSER]: https://github.com/Bogdanp/dramatiq/blob/master/COPYING.LESSER
[COPYING]: https://github.com/Bogdanp/dramatiq/blob/master/COPYING
[RabbitMQ]: https://www.rabbitmq.com/
[Redis]: https://redis.io
[user guide]: https://dramatiq.io/guide.html
