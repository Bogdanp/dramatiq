# Celery vs Dramatiq benchmarks

## Setup

1. Install [memcached][memcached] and [RabbitMQ][rabbitmq] or [Redis][redis]
1. Install Dramatiq: `pip install dramatiq[rabbitmq]` or `pip install dramatiq[redis]`
1. Install the dependencies: `pip install -r requirements.txt`
1. Run `redis-server` or `rabbitmq-server` in a terminal window.
1. In a separate terminal window, run `memcached`.

## Running the benchmarks

Run `python bench.py` to run the Dramatiq benchmark, and `python
bench.py --use-celery` to run the Celery benchmark.  Prepend `env
REDIS=1` to each command to run the benchmarks against Redis.

Run `python bench.py --help` to see all the available options.

## Caveats

As with any benchmark, take it with a grain of salt.  Dramatiq has an
advantage over Celery in most of these benchmarks by design.


[memcached]: https://memcached.org
[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
