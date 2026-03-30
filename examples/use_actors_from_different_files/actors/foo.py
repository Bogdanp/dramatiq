import dramatiq

# Import my_broker module to ensure set_broker() is called before @actor is used.
import my_broker


@dramatiq.actor(broker=my_broker.rabbitmq_broker)
def foo_task():
    print("Foo task done.")
