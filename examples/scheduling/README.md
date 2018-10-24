# Remoulade Scheduling Example

This example demonstrates how to use Remoulade in conjunction with
[APScheduler] in order to schedule messages.

## Running the Example

1. Install [RabbitMQ][rabbitmq] and [Redis][redis]
1. Install remoulade: `pip install remoulade[rabbitmq,redis]`
1. Install apscheduler: `pip install apscheduler`
1. Run RabbitMQ: `rabbitmq-server`
1. Run Redis: `redis-server`
1. In a separate terminal window, run the workers: `remoulade example`.
1. In another terminal, run `python -m example`.


[APScheduler]: https://apscheduler.readthedocs.io/en/latest/
[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
