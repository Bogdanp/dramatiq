<img src="https://dramatiq.io/_static/logo.png" align="right" width="131" />

# dramatiq

[![Build Status](https://travis-ci.org/Bogdanp/dramatiq.svg?branch=master)](https://travis-ci.org/Bogdanp/dramatiq)
[![PyPI version](https://badge.fury.io/py/dramatiq.svg)](https://badge.fury.io/py/dramatiq)
[![Documentation](https://img.shields.io/badge/doc-latest-brightgreen.svg)](http://dramatiq.io)
[![Discourse](https://img.shields.io/badge/discuss-online-orange.svg)](https://reddit.com/r/dramatiq)

*A fast and reliable distributed task processing library for Python 3.*

<hr/>

**Changelog**: https://dramatiq.io/changelog.html <br/>
**Community**: https://reddit.com/r/dramatiq <br/>
**Documentation**: https://dramatiq.io <br/>
**Professional Support**: [https://tidelift.com](https://tidelift.com/subscription/pkg/pypi-dramatiq?utm_source=pypi-dramatiq&utm_medium=referral&utm_campaign=readme)

<hr/>

## Installation

If you want to use it with [RabbitMQ]

    pipenv install 'dramatiq[rabbitmq, watch]'

or if you want to use it with [Redis]

    pipenv install 'dramatiq[redis, watch]'


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
