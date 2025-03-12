# Using Actors from Different Files

## Overview

If you want to use actors from different files in your project, you must ensure that all actors are properly initialized and visible to Dramatiq. This example demonstrates how to set up a project with multiple actor files and run them through the Dramatiq CLI.

## Project Structure

```
project/
├── core/
│   ├── dramatiq_service.py
├── tasks/
│   ├── foo/
│   │   ├── __init__.py
│   │   ├── tasks.py
│   ├── bar/
│   │   ├── __init__.py
│   │   ├── tasks.py
│   ├── __init__.py
├── main.py
```

- `tasks/`: Contains actor definitions (`foo/tasks.py`, `bar/tasks.py`).
- `dramatiq_service.py`: Initializes the broker and imports all actors.
- `main.py`: FastAPI application.

## Setup

1. **Broker Initialization (`dramatiq_service.py`)**

```python
import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.middleware import AsyncIO

# Initialize RabbitMQ broker
rabbitmq_broker = RabbitmqBroker(url="amqp://guest:guest@localhost:5672")
rabbitmq_broker.add_middleware(AsyncIO())
dramatiq.set_broker(rabbitmq_broker)

# Import all actors
from tasks.bar import *  # Ensure all actors are imported
from tasks.foo import *
```

2. **Actor Definitions**

`tasks/bar/tasks.py`:

```python
import dramatiq

@dramatiq.actor
def bar_task():
    print("Bar task done.")
```

`tasks/foo/tasks.py`:

```python
import dramatiq

@dramatiq.actor
def foo_task():
    print("Foo task done.")
```

3. **FastAPI Endpoint (`main.py`)**

```python
from fastapi import FastAPI
from tasks.bar.tasks import bar_task
from tasks.foo.tasks import foo_task

app = FastAPI()

@app.get("/test-task")
def test_task():
    bar_task.send()
    foo_task.send()
    return {"message": "Tasks sent"}
```

## Steps to Run

1. **Start the FastAPI application**:

```
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

2. **Run the Dramatiq worker**:

```
dramatiq core.dramatiq_service
```

3. **Trigger tasks by making a GET request**:

```
curl http://localhost:8001/test-task
```

4. **Check the logs in the Dramatiq terminal**:

```
Bar task done.
Foo task done.
```

## Optional Enhancements

### Use Automatic Task Registration

Instead of manually importing actors in `dramatiq_service.py`:

```python
from tasks.bar import *  # Manual import
from tasks.foo import *  # Manual import
```

You can replace it with an **automatic task registration** method, which dynamically imports all modules with tasks under the `tasks` package.

**How to Implement**:

Add the following function to `dramatiq_service.py`:

```python
import pkgutil
import importlib

def auto_register_tasks(base_package: str):
    """
    Automatically imports all modules within the specified base package.

    Args:
        base_package (str): The root package containing task modules.
    """
    for module_info in pkgutil.iter_modules([base_package.replace(".", "/")]):
        importlib.import_module(f"{base_package}.{module_info.name}")
```

Replace the manual imports with a call to `auto_register_tasks`:

```python
# Manual imports
# from tasks.bar import *
# from tasks.foo import *

# Use automatic task registration
auto_register_tasks("tasks")
```

### Important Note
It is crucial to call `auto_register_tasks` in the exact same location where the manual imports were previously defined. This ensures that all tasks are registered before the Dramatiq worker starts. Failing to do this will result in tasks not being visible to the Dramatiq CLI.

## Conclusion

This setup ensures that actors from `multiple files` are visible to `Dramatiq` while maintaining scalability and organization.
