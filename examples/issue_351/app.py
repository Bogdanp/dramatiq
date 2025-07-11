import dramatiq


@dramatiq.actor
def foo():
    a = tuple(range(5000000))  # noqa: F841
    raise Exception("bar")


if __name__ == "__main__":
    for _ in range(10):
        foo.send()
