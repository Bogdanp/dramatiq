# Remoulade Results Example

This example demonstrates how to use Remoulade actors to store and
retrieve task results.

## Running the Example

1. Install [RabbitMQ][rabbitmq] and [Redis][redis]
1. Install remoulade: `pip install remoulade[rabbitmq,redis]`
1. Run RabbitMQ: `rabbitmq-server`
1. Run Redis: `redis-server`
1. In a separate terminal window, run the workers: `remoulade example`.
1. In another terminal, run `python -m example`.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
