<img src="https://dramatiq.io/_static/logo.png" align="right" width="131" />

# dramatiq

[![Build Status](https://travis-ci.org/Bogdanp/dramatiq.svg?branch=master)](https://travis-ci.org/Bogdanp/dramatiq)
[![Test Coverage](https://api.codeclimate.com/v1/badges/2e03a54d3d3ee0bb93c4/test_coverage)](https://codeclimate.com/github/Bogdanp/dramatiq/test_coverage)
[![Maintainability](https://api.codeclimate.com/v1/badges/2e03a54d3d3ee0bb93c4/maintainability)](https://codeclimate.com/github/Bogdanp/dramatiq/maintainability)
[![PyPI version](https://badge.fury.io/py/dramatiq.svg)](https://badge.fury.io/py/dramatiq)
[![Documentation](https://img.shields.io/badge/doc-latest-brightgreen.svg)](http://dramatiq.io)

**dramatiq** is a distributed task processing library for Python with
a focus on simplicity, reliability and performance.

Here's what it looks like:

``` python
import dramatiq
import requests

@dramatiq.actor
def count_words(url):
   response = requests.get(url)
   count = len(response.text.split(" "))
   print(f"There are {count} words at {url!r}.")

# Synchronously count the words on example.com in the current process
count_words("http://example.com")

# or send the actor a message so that it may perform the count
# later, in a separate process.
count_words.send("http://example.com")
```

## Installation

If you want to use it with [RabbitMQ][rabbit]

    pip install -U dramatiq[rabbitmq, watch]

or if you want to use it with [Redis][redis]

    pip install -U dramatiq[redis, watch]

## Documentation

Documentation is available at http://dramatiq.io

## License

dramatiq is licensed under the AGPL.  Please see [LICENSE][license]
for licensing details.

Commercial licensing options are available [upon request][commercial].


[commercial]: https://dramatiq.io/commercial.html
[license]: https://github.com/Bogdanp/dramatiq/blob/master/LICENSE
[rabbit]: https://www.rabbitmq.com/
[redis]: https://redis.io
