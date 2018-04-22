# Dramatiq Persistent Example

This example demonstrates long-running tasks in Dramatiq that are durable to
worker shutdowns by using simple state persistence.

## Running the Example

1. Install [RabbitMQ][rabbitmq] or [Redis][redis]
1. Install dramatiq: `pip install dramatiq[rabbitmq]` or `pip install dramatiq[redis]`
1. Run RabbitMQ: `rabbitmq-server` or Redis: `redis-server`
1. In a separate terminal window, run the workers: `dramatiq example`.
   Add `REDIS=1` before `dramatiq` to use the Redis broker.
1. In another terminal, run `python -m example <n>` to enqueue a task.
1. To test the persistence, terminate the worker process with `crtl-c`, then
   restart with the same `n` value.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
