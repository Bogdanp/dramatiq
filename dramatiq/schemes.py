from typing import List, Optional
from abc import ABC, abstractmethod
from uuid import UUID, uuid4
import random

from .middleware import Middleware
from .rate_limits import Barrier
from .rate_limits.backend import RateLimiterBackend
from .broker import Broker
from .message import Message


class GroupStart:
    def __init__(self, *, id: str, count: int):
        """An object to describe a group to start."""
        self.id = id
        self.count = count

    def __repr__(self):
        return f'GroupStart(id={self.id!r}, count={self.count!r})'


class Schemes(Middleware):
    """Middleware to enable complex task groupings."""

    def __init__(self, backend: RateLimiterBackend, ttl: int):
        self.backend = RateLimiterBackend
        self.ttl = ttl

    def barrier(self, group_id):
        return Barrier(self.backend, group_id, ttl=self.ttl)

    def start_group(group_start):
        """Start the group expecting count messages."""
        return self.barrier(group_start.id).create(parties=group_start.count)

    def check_group(group_id):
        """Check if this is the last message in the group."""
        return self.barrier(group_id).wait(block=False)

    def process(self, *, group_ids=(), starts=(), targets=()):
        if  not all([self.check_group(group_id) for group_id in group_ids]):
                return  # There are more messages left in the group.

        for start in starts:
            self.start_group(start)

        for target in targets:
            broker.enqueue(target)

    def after_process_message(
        self, broker: Broker, message: Message, *,
        result=None, exception=None,
    ):
        if exception is not None:
            return

        group_ids = message.options.get('scheme_group_ids', [])
        starts = [
            GroupStart(**start)
            for start in message.options.get('scheme_starts', [])
        ]
        targets = [
            Message(**target)
            for target in message.options.get('scheme_targets', [])
        ]
        self.process(group_ids=group_ids, starts=starts, targets=targets)


class Finalizable(ABC):
    @abstractmethod
    def finalize(self) -> 'Targetable':
        """Finalize this set of tasks."""
        raise NotImplementedError


class Enqueueable(Finalizable):
    def enqueue(self, broker: Broker, delay: Optional[int] = None):
        """Enqueue this set of tasks."""
        finalized = self.finalize()
        starts = finalized.target_starts()
        targets = finalized.target_messages()
        middleware = next(filter(lambda m: isinstance(m, Schemes)), None)
        assert middleware, 'No Schemes middleware could be found in the broker'
        middleware.process(starts=starts, targets=targets)
        return finalized


class Targetable(Finalizable):
    @abstractmethod
    def target_messages(self) -> List[Message]:
        """Get the messages that should start when this target starts."""
        raise NotImplementedError

    @abstractmethod
    def target_starts(self) -> List[GroupStart]:
        """Get the groups that should start when this target starts."""
        raise NotImplementedError


class Chainable(Targetable):
    @abstractmethod
    def with_target(self, target: Optional[Targetable]) -> 'Chainable':
        """Assign a target."""
        raise NotImplementedError


class Groupable(Finalizable):
    @abstractmethod
    def with_group(self, group: 'Group') -> 'Groupable':
        """Assign to a group."""
        raise NotImplementedError

    @abstractmethod
    def count_messages(self) -> int:
        """Count the messages that are part of completing the group."""
        raise NotImplementedError


class Single(Enqueueable, Chainable, Groupable):
    def __init__(
        self, message: Message, *,
        target: Optional[Targetable] = None,
        group: Optional['Group'] = None,
    ):
        self.__message = message
        self.__target = target
        self.__group = group

    def __repr__(self):
        return repr(self.__message)

    def finalize(self) -> 'Single':
        options = {}
        if self.__target:
            target_messages = self.__target.target_messages()
            target_starts = self.__target.target_starts()
            if target_messages:
                options['scheme_targets'] = [
                    message.asdict()
                    for message in target_messages
                ]
            if target_starts:
                options['scheme_starts'] = [
                    {
                        'id': start.id,
                        'count': start.count,
                    }
                    for start in target_starts
                ]
        if self.__group:
            options.setdefault('scheme_group_ids', [])
            options['scheme_group_ids'].extend(self.__group.group_ids())
        finalized = self.__message.copy(message_id=None, options=options)
        return type(self)(finalized, target=self.__target, group=self.__group)

    def target_messages(self) -> List[Message]:
        return [self.__message]

    def target_starts(self) -> List[GroupStart]:
        return []

    def with_target(self, target: Optional[Targetable]) -> 'Single':
        return type(self)(self.__message, target=target, group=self.__group)

    def with_group(self, group: 'Group') -> 'Single':
        return type(self)(self.__message, target=self.__target, group=group)

    def count_messages(self) -> int:
        return 1


class Chain(Enqueueable, Chainable, Groupable):
    def __init__(
        self, children: List[Chainable], *,
        target: Optional[Targetable] = None,
        group: Optional['Group'] = None,
    ):
        self.__children = children
        self.__target = target
        self.__group = group

    def __repr__(self):
        return f'Chain({self.__children!r})'

    def finalize(self) -> 'Chain':
        children = self.__children + ([self.__target] if self.__target else [])
        finalized = []
        target = children[-1].with_group(self.__group).finalize()
        finalized.append(target)

        for child in reversed(children[:-1]):
            target = child.with_target(target).finalize()
            finalized.append(target)

        target = self.__target and finalized[0]
        children = list(reversed(finalized[1:] if target else finalized))
        return type(self)(children, target=target, group=self.__group)

    def target_messages(self) -> List[Message]:
        return self.__children[0].target_messages()

    def target_starts(self) -> List[GroupStart]:
        return []

    def with_target(self, target: Optional[Targetable]) -> 'Chain':
        return type(self)(self.__children, target=target, group=self.__group)

    def with_group(self, group: Optional['Group']) -> 'Chain':
        return type(self)(self.__children, target=self.__target, group=group)

    def count_messages(self) -> int:
        return (self.__target or self.__children[-1]).count_messages()


class Group(Enqueueable, Chainable, Groupable):
    def __init__(
        self, children: List[Groupable], *,
        target: Optional[Targetable] = None,
        group: Optional['Group'] = None,
    ):
        self.__children = children
        self.id = str(uuid4())
        self.__target = target
        self.__group = group

    def __repr__(self):
        return f'Group({self.__children!r})'

    def finalize(self) -> 'Group':
        children = []
        group = type(self)(children, target=self.__target, group=self.__group)
        for child in self.__children:
            children.append(child.with_group(group).finalize())
        return group

    def target_messages(self) -> List[Message]:
        return [
            message for child in self.__children
            for message in child.target_messages()
        ]

    def target_starts(self) -> List[GroupStart]:
        return [
            start for child in self.__children
            for start in child.target_starts()
        ] + [GroupStart(id=self.id, count=self.count_messages())]

    def with_target(self, target: Optional[Targetable]) -> 'Group':
        return type(self)(self.__children, target=target, group=self.__group)

    def with_group(self, group: 'Group') -> 'Group':
        return type(self)(self.__children, target=self.__target, group=group)

    def group_ids(self) -> List[str]:
        """Get the group ids for this group and parent groups."""
        parent_ids = self.__group.group_ids() if self.__group else []
        return [self.id] + parent_ids

    def count_messages(self) -> int:
        return sum(child.count_messages() for child in self.__children)
