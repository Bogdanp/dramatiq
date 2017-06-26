# Celery vs Dramatiq latency benchmark

This benchmark compares how well Dramatiq and Celery fare when running
some number of latency-bound tasks.

## Setup

1. Install [memcached][memcached] and [RabbitMQ][rabbitmq] or [Redis][redis]
1. Install dramatiq: `pip install dramatiq[rabbitmq]` or `pip install dramatiq[redis]`
1. Install the dependencies: `pip install -r requirements.txt`
1. Run `redis-server` or `rabbitmq-server` in a terminal window.
1. In a separate terminal window, run `memcached`.

## Running the benchmark

Run `python latency.py` to run the Dramatiq benchmark, and `python
latency.py --use-celery` to run the Celery benchmark.  Prepend `env
REDIS=1` to each command to run the benchmarks against Redis.

## Caveats

As with any benchmark, take it with a grain of salt.  Dramatiq has an
advantage over Celery here by design (workers are multi-threaded).


[memcached]: https://memcached.org
[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
