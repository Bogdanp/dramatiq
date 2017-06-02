# dramatiq example

## Running the example

1. Install [RabbitMQ][rabbitmq]
1. Install dramatiq: `pip install dramatiq[rabbitmq]`
1. Run RabbitMQ: `rabbitmq-server`
1. In a separate terminal window, run the workers: `env PYTHONPATH=. dramatiq example`
1. In a separate terminal window, run the script: `python -m example`


[rabbitmq]: https://www.rabbitmq.com/
