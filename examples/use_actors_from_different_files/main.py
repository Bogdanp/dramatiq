# Import Broker first so it is set up.
import my_broker  # noqa: F401

# Import actors after broker.
import actors


def my_app():
    """Basic application that publishes some messages."""
    actors.bar_task.send()
    actors.foo_task.send()


if __name__ == "__main__":
    my_app()
