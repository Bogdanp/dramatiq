import dramatiq


@dramatiq.actor
async def bar_task():
    print("Bar task done.")
