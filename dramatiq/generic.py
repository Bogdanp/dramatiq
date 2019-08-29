# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from . import actor


class generic_actor(type):
    """Meta for class-based actors.
    """

    def __new__(metacls, name, bases, attrs):
        clazz = super().__new__(metacls, name, bases, attrs)
        meta = getattr(clazz, "Meta", object())
        if not getattr(meta, "abstract", False):
            options = {name: getattr(meta, name) for name in vars(meta) if not name.startswith("_")}
            options.pop("abstract", False)

            clazz_instance = clazz()
            actor_registry = options.pop("actor", actor)
            actor_instance = actor_registry(clazz_instance, **options)
            setattr(clazz, "__getattr__", generic_actor.__getattr__)
            setattr(clazz_instance, "__actor__", actor_instance)
            return clazz_instance

        setattr(meta, "abstract", False)
        return clazz

    def __getattr__(cls, name):
        return getattr(cls.__actor__, name)


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
      ...     class Meta:
      ...         abstract = True
      ...         queue_name = "tasks"
      ...         max_retries = 20
      ...
      ...     def get_task_name(self):
      ...         raise NotImplementedError
      ...
      ...     def perform(self):
      ...         print(f"Hello from {self.get_task_name()}!")

      >>> class FooTask(BaseTask):
      ...     def get_task_name(self):
      ...         return "Foo"

      >>> class BarTask(BaseTask):
      ...     def get_task_name(self):
      ...         return "Bar"

      >>> FooTask.send()
      >>> BarTask.send()

    Attributes:
      logger(Logger): The actor's logger.
      broker(Broker): The broker this actor is bound to.
      actor_name(str): The actor's name.
      queue_name(str): The actor's queue.
      priority(int): The actor's priority.
      options(dict): Arbitrary options that are passed to the broker
        and middleware.
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
        raise NotImplementedError("%s does not implement perform()" % self.__name__)
