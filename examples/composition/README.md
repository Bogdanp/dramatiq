# Remoulade Composition Example

This example demonstrates how to use Remoulade's high level composition
abstractions.

## Running the Example

1. Install [RabbitMQ][rabbitmq] and [Redis][redis]
1. Install remoulade and requests: `pip install remoulade[rabbitmq,redis] requests`
1. Run RabbitMQ: `rabbitmq-server`
1. Run Redis: `redis-server`
1. In a separate terminal window, run the workers: `remoulade example`.
1. In another terminal, run `python -m example`.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
