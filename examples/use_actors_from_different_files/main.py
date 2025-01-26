from fastapi import FastAPI

from tasks.bar.tasks import bar_task
from tasks.foo.tasks import foo_task


app = FastAPI()


@app.get("/test-task")
async def test_task():
    foo_task.send()
    bar_task.send()
    return {"message": "Tasks sent."}
