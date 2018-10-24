<img src="https://remoulade.io/_static/logo.png" align="right" width="131" />

# remoulade

[![Build Status](https://travis-ci.org/wiremind/remoulade.svg?branch=master)](https://travis-ci.org/wiremind/remoulade)
[![PyPI version](https://badge.fury.io/py/remoulade.svg)](https://badge.fury.io/py/remoulade)
[![Documentation](https://img.shields.io/badge/doc-latest-brightgreen.svg)](http://remoulade.io)

*A fast and reliable distributed task processing library for Python 3.*

<hr/>

**Changelog**: https://remoulade.io/changelog.html <br/>
**Documentation**: https://remoulade.io

<hr/>


## Installation

If you want to use it with [RabbitMQ]

    pipenv install 'remoulade[rabbitmq, watch]'

or if you want to use it with [Redis]

    pipenv install 'remoulade[redis, watch]'


## Quickstart

Make sure you've got [RabbitMQ] running, then create a new file called
`example.py`:

``` python
import remoulade
import requests
import sys

@remoulade.actor
def count_words(url):
    response = requests.get(url)
    count = len(response.text.split(" "))
    print(f"There are {count} words at {url!r}.")


if __name__ == "__main__":
    count_words.send(sys.argv[1])
```

In one terminal, run your workers:

    remoulade example

In another, start enqueueing messages:

    python example.py http://example.com
    python example.py https://github.com
    python example.py https://news.ycombinator.com

Check out the [user guide] to learn more!


## License

remoulade is licensed under the LGPL.  Please see [COPYING] and
[COPYING.LESSER] for licensing details.


[COPYING.LESSER]: https://github.com/wiremind/remoulade/blob/master/COPYING.LESSER
[COPYING]: https://github.com/wiremind/remoulade/blob/master/COPYING
[RabbitMQ]: https://www.rabbitmq.com/
[Redis]: https://redis.io
[user guide]: https://remoulade.io/guide.html
