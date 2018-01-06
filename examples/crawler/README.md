# Dramatiq Web Crawler Example

This example implements a very simple distributed web crawler using
Dramatiq.

## Running the Example

1. Install [RabbitMQ][rabbitmq] or [Redis][redis]
1. Install dramatiq: `pip install dramatiq[rabbitmq]` or `pip install dramatiq[redis]`
1. Install the example's dependencies: `pip install -r requirements.txt`
1. Run `redis-server` or `rabbitmq-server` in a terminal window.
1. In a separate terminal, run `dramatiq example` to run the workers.
   If you want to use the Redis broker, add `REDIS=1` before
   `dramatiq`.
1. Finally, run `python example.py https://example.com` to begin
   crawling http://example.com.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
