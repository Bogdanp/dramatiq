# Celery vs Remoulade benchmarks

## Setup

1. Install [RabbitMQ][rabbitmq] and [Redis][redis]
1. Install Remoulade: `pip install remoulade[rabbitmq]` or `pip install remoulade[redis]`
1. Install the dependencies: `pip install -r requirements.txt`
1. Run `redis-server` or `rabbitmq-server` in a terminal window.
1. In a separate terminal window, run `redis-server`.

## Running the benchmarks

Run `python bench.py` to run the Remoulade benchmark, and `python
bench.py --use-celery` to run the Celery benchmark.  Prepend `env
REDIS=1` to each command to run the benchmarks against Redis.

Run `python bench.py --help` to see all the available options.

## Caveats

As with any benchmark, take it with a grain of salt.  Remoulade has an
advantage over Celery in most of these benchmarks by design.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
