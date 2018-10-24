# Remoulade Persistent Example

This example demonstrates long-running tasks in Remoulade that are durable to
worker shutdowns by using simple state persistence.

## Running the Example

1. Install [RabbitMQ][rabbitmq] or [Redis][redis]
1. Install remoulade: `pip install remoulade[rabbitmq]` or `pip install remoulade[redis]`
1. Run RabbitMQ: `rabbitmq-server` or Redis: `redis-server`
1. In a separate terminal window, run the workers: `remoulade example`.
   Add `REDIS=1` before `remoulade` to use the Redis broker.
1. In another terminal, run `python -m example <n>` to enqueue a task.
1. To test the persistence, terminate the worker process with `crtl-c`, then
   restart with the same `n` value.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
