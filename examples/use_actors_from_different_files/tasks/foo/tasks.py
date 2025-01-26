import dramatiq


@dramatiq.actor
async def foo_task():
    print("Foo task done.")