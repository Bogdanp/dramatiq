from . import actor


class generic_actor(type):
    """Meta for class-based actors.
    """

    def __new__(cls, name, bases, attrs):
        clazz = super().__new__(cls, name, bases, attrs)
        meta = getattr(clazz, "Meta", object())
        if not getattr(meta, "abstract", False):
            options = {name: getattr(meta, name) for name in vars(meta) if not name.startswith("_")}
            options.pop("abstract", False)
            return actor(clazz(), **options)

        setattr(meta, "abstract", False)
        return clazz


class GenericActor(metaclass=generic_actor):
    """Base-class for class-based actors.

    Each subclass may define an inner class named ``Meta``.  You can
    use the meta class to provide broker options for the actor.

    Classes that have ``abstract = True`` in their meta class are
    considered abstract base classes and are not converted into
    actors.  You can't send these classes messages, you can only
    inherit from them.  Actors that subclass abstract base classes
    inherit their parents' meta classes.

    Example:

      >>> class BaseTask(GenericActor):
      ...   class Meta:
      ...     abstract = True
      ...     queue_name = "tasks"
      ...     max_retries = 20
      ...
      ...   def get_task_name(self):
      ...     raise NotImplementedError
      ...
      ...   def perform(self):
      ...     print(f"Hello from {self.get_task_name()}!")
      ...

      >>> class FooTask(BaseTask):
      ...   def get_task_name(self):
      ...     return "Foo"

      >>> class BarTask(BaseTask):
      ...   def get_task_name(self):
      ...     return "Bar"

      >>> FooTask.send()
      >>> BarTask.send()

    """

    class Meta:
        abstract = True

    @property
    def __name__(self):
        """The default name of this actor.
        """
        return type(self).__name__

    def __call__(self, *args, **kwargs):
        return self.perform(*args, **kwargs)

    def perform(self):
        """This is the method that gets called when the actor receives
        a message.  All non-abstract subclasses must implement this
        method.
        """
        raise NotImplementedError(f"{self.__name__} does not implement perform()")
