<img src="https://dramatiq.io/_static/logo.png" align="right" width="131" />

# dramatiq

[![Build Status](https://github.com/Bogdanp/dramatiq/workflows/CI/badge.svg)](https://github.com/Bogdanp/dramatiq/actions?query=workflow%3A%22CI%22)
[![PyPI version](https://badge.fury.io/py/dramatiq.svg)](https://badge.fury.io/py/dramatiq)
[![Documentation](https://img.shields.io/badge/doc-latest-brightgreen.svg)](http://dramatiq.io)
[![Discuss](https://img.shields.io/badge/discuss-online-orange.svg)](https://groups.io/g/dramatiq-users)

*A fast and reliable distributed task processing library for Python 3.*

<hr/>

**Changelog**: https://dramatiq.io/changelog.html <br/>
**Community**: https://groups.io/g/dramatiq-users <br/>
**Documentation**: https://dramatiq.io <br/>

<hr/>

<h3 align="center">Sponsors</h3>

<p align="center" dir="auto">
  <a href="https://franz.defn.io" target="_blank">
    <img width="64px" src="docs/source/_static/franz-logo.png" />
  </a>
  <a href="https://podcatcher.defn.io" target="_blank">
    <img width="64px" src="docs/source/_static/podcatcher-logo.png" />
  </a>
</p>


## Installation

If you want to use it with [RabbitMQ]

    pip install 'dramatiq[rabbitmq, watch]'

or if you want to use it with [Redis]

    pip install 'dramatiq[redis, watch]'


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
