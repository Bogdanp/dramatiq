import functools
from typing import Callable, Any, Dict, List, Optional, Union, TYPE_CHECKING

# Attempt to import real Dramatiq classes. If not available, use mocks.
try:
    from dramatiq import Broker, Actor
    _HAS_REAL_DRAMATIQ = True
except ImportError:
    _HAS_REAL_DRAMATIQ = False

    if TYPE_CHECKING:
        # Define placeholder types for type checkers even if real dramatiq is not imported
        class Broker: # type: ignore
            def actor(self, fn: Optional[Callable] = None, **options: Any) -> Callable: ...
        class Actor: # type: ignore
            def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
            def send(self, *args: Any, **kwargs: Any) -> Any: ...

    class MockBroker:
        """A minimal mock for dramatiq.Broker for testing purposes."""
        def actor(self, fn: Optional[Callable] = None, **options: Any) -> Callable:
            def decorator(func: Callable) -> 'MockActor':
                return MockActor(func, self, options)
            if fn:
                return decorator(fn)
            return decorator

    class MockActor:
        """A minimal mock for dramatiq.Actor for testing purposes."""
        def __init__(self, func: Callable, broker: 'MockBroker', options: Dict[str, Any]):
            functools.wraps(func)(self)
            self.func = func
            self.broker = broker
            self.options = options

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self.func(*args, **kwargs)

        def send(self, *args: Any, **kwargs: Any) -> Any:
            # In a real scenario, this would put a message on the queue.
            # For the mock, we simulate synchronous execution.
            return self.func(*args, **kwargs)

        def __repr__(self) -> str:
            return f"<MockActor '{self.func.__name__}'>"

    Broker = MockBroker
    Actor = MockActor


class PendingActorWrapper:
    """
    A wrapper returned by the registry's actor decorator when no broker
    is yet bound. It stores the original function and options, and
    delegates to the actual Dramatiq Actor once bound.
    """
    def __init__(self, func: Callable, options: Dict[str, Any]):
        functools.wraps(func)(self)
        self._original_func = func
        self._options = options
        self._actual_actor: Optional[Actor] = None

    def _ensure_actor_bound(self):
        """Internal helper to ensure the actual actor is bound before broker methods are called."""
        if self._actual_actor is None:
            raise RuntimeError(
                f"Task '{self._original_func.__name__}' cannot be sent/called "
                "via broker methods (like .send()) before a broker is bound to the registry. "
                "Did you call registry.bind_broker()?"
            )

    @property
    def __wrapped__(self) -> Callable:
        """Allows access to the original function using __wrapped__."""
        return self._original_func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        When the decorated function is called directly, it executes the
        original function synchronously. This is useful for local testing
        or if the task is intended to run synchronously in some contexts.
        """
        return self._original_func(*args, **kwargs)

    def send(self, *args: Any, **kwargs: Any) -> Any:
        """
        Delegates the 'send' call to the actual Dramatiq Actor once it's bound.
        """
        self._ensure_actor_bound()
        return self._actual_actor.send(*args, **kwargs)

    def __repr__(self) -> str:
        status = "bound" if self._actual_actor else "pending"
        return f"<PendingActorWrapper '{self._original_func.__name__}' ({status})>"

    def _bind_actual_actor(self, actual_actor: Actor):
        """Internal method to set the actual Dramatiq Actor instance."""
        expected_type = Actor if _HAS_REAL_DRAMATIQ else MockActor # type: ignore
        if not isinstance(actual_actor, expected_type):
            raise TypeError(f"Expected a Dramatiq Actor instance, got {type(actual_actor)}")
        self._actual_actor = actual_actor


class TaskRegistry:
    """
    A registry to collect Dramatiq tasks (actors) without requiring an
    active Broker instance at definition time. This decouples task declaration
    from immediate broker availability, allowing for more flexible application
    startup sequences.
    """
    def __init__(self):
        self._pending_actor_wrappers: List[PendingActorWrapper] = []
        self._bound_broker: Optional[Broker] = None
        # Map original function to its PendingActorWrapper for retrieval
        self._func_to_wrapper: Dict[Callable, PendingActorWrapper] = {}

    def actor(self, fn: Optional[Callable] = None, **options: Any) -> Union[Callable[[Callable], PendingActorWrapper], PendingActorWrapper]:
        """
        A decorator to register a Dramatiq actor with this registry.
        Tasks decorated with this will be registered with a Broker once
        `bind_broker` is called. It returns a `PendingActorWrapper` which
        can be called synchronously or eventually send messages to the queue
        once the broker is bound.
        """
        def decorator(func: Callable) -> PendingActorWrapper:
            if not callable(func):
                raise TypeError("actor decorator must be applied to a callable function.")

            # Create a PendingActorWrapper immediately for the decorated function
            wrapper = PendingActorWrapper(func, options)
            self._func_to_wrapper[func] = wrapper

            if self._bound_broker is not None:
                # If a broker is already bound, create and bind the actual actor immediately
                actual_actor = self._bound_broker.actor(func, **options)
                wrapper._bind_actual_actor(actual_actor)
            else:
                # Otherwise, store the wrapper for later processing
                self._pending_actor_wrappers.append(wrapper)

            return wrapper
        
        # This handles both @registry.actor and @registry.actor(...)
        if fn is None:
            return decorator
        return decorator(fn)

    def bind_broker(self, broker: Broker):
        """
        Binds a Dramatiq Broker instance to this registry.
        All pending actors will be registered with this broker.
        This method can only be called once per registry instance.
        """
        expected_type = Broker if _HAS_REAL_DRAMATIQ else MockBroker # type: ignore
        if not isinstance(broker, expected_type):
            raise TypeError(f"Expected a dramatiq.Broker instance, got {type(broker)}")

        if self._bound_broker is not None:
            raise RuntimeError("A broker has already been bound to this registry.")

        self._bound_broker = broker
        
        # Process all previously collected pending actor wrappers
        for wrapper in self._pending_actor_wrappers:
            # __wrapped__ is preferred for getting the original function passed to functools.wraps
            actual_actor = self._bound_broker.actor(wrapper.__wrapped__, **wrapper._options)
            wrapper._bind_actual_actor(actual_actor)
        self._pending_actor_wrappers.clear() # Clear the list of pending wrappers

    def get_actor_wrapper(self, func: Callable) -> Optional[PendingActorWrapper]:
        """
        Retrieves the PendingActorWrapper for a given original function.
        This can be useful for introspection or advanced interactions.
        """
        return self._func_to_wrapper.get(func)

# Create a default registry instance for convenience.
# Applications can import this `registry` instance and use its `@registry.actor` decorator.
registry = TaskRegistry()