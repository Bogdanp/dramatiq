# Dramatiq Composition Example

This example demonstrates how to use Dramatiq's high level composition
abstractions.

## Running the Example

1. Install [RabbitMQ][rabbitmq] and [Redis][redis]
1. Install dramatiq and requests: `pip install dramatiq[rabbitmq,redis] requests`
1. Run RabbitMQ: `rabbitmq-server`
1. Run Redis: `redis-server`
1. In a separate terminal window, run the workers: `dramatiq example`.
1. In another terminal, run `python -m example`.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
