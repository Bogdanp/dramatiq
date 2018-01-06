# Dramatiq Time Limit Example

This example demonstrates the time limit feature of Dramatiq.

## Running the Example

1. Install [RabbitMQ][rabbitmq] or [Redis][redis]
1. Install dramatiq: `pip install dramatiq[rabbitmq]` or `pip install dramatiq[redis]`
1. Run RabbitMQ: `rabbitmq-server` or Redis: `redis-server`
1. In a separate terminal window, run the workers: `dramatiq example`.
   Add `REDIS=1` before `dramatiq` to use the Redis broker.
1. In another terminal, run `python -m example` to enqueue a task.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
