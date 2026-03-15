# Using Actors from Different Files

## Overview

If you want to use actors from different files in your project, you must ensure that all 
actors are properly initialized and visible to Dramatiq. This example demonstrates one 
possible way to set up a project with multiple actor files and run them through the 
Dramatiq CLI.

## Project Structure

```text
project/
├── actors/
│   ├── __init__.py
│   ├── bar.py
│   ├── foo.py
├── main.py
├── my_broker.py
```

- `actors/`: Contains actor definitions (`foo.py`, `bar.py`).
- `my_broker.py`: Initializes the broker.
- `main.py`: Application that publishes messages.

## Steps to Run

1. **Run the Dramatiq worker**:

In a terminal, start a worker with the following command

```shell
dramatiq my_broker actors
```

It is important to note:
* The first argument must be the module that initializes the Broker.
  Because we are using a plain module name, it must call `set_broker()`.
* The subsequent arguments are extra modules to import that contain actor definitions.
  In this case, only our `actors` module.

2. **Publish tasks by running the application**:

In another terminal, run the application that publishes some messages.
This could be a webserver, or a cron-like scheduler.
In this example it is a simple script.

```shell
python main.py
```

3. **Check the logs in the Dramatiq worker terminal**:

Back in the first terminal, check the worker logs to see that the actors have run.

```text
Bar task done.
Foo task done.
```

## Conclusion

This example is just one way of organizing actors into multiple files, but not the only way.

The two key rules to remember are:

1. Call `set_broker()` before importing any module that uses `@actor`.
   This ensures that `@actor` will use the correct Broker.
   This can be enforced by importing your broker-defining module in any actor-defining module,
   like in this example.
2. Modules that are passed to the worker command line must import (directly or indirectly)
   all actors. This ensures that the dramatiq worker is aware of all actors.
