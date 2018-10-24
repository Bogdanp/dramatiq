# Remoulade Web Crawler Example

This example implements a very simple distributed web crawler using
Remoulade.

## Running the Example

1. Install [RabbitMQ][rabbitmq] or [Redis][redis]
1. Install remoulade: `pip install remoulade[rabbitmq]` or `pip install remoulade[redis]`
1. Install the example's dependencies: `pip install -r requirements.txt`
1. Run `redis-server` or `rabbitmq-server` in a terminal window.
1. In a separate terminal, run `remoulade example` to run the workers.
   If you want to use the Redis broker, add `REDIS=1` before
   `remoulade`.
1. Finally, run `python example.py https://example.com` to begin
   crawling http://example.com.


[rabbitmq]: https://www.rabbitmq.com
[redis]: https://redis.io
