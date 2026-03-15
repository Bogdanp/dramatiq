"""Module to define actors"""

# Import actors from submodules to ensure they are registered when this `actors` module is imported.
from .bar import bar_task
from .foo import foo_task

__all__ = ["bar_task", "foo_task"]
