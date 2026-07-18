from dataclasses import dataclass, field
from datetime import date
from typing import Final


class UnsetValue:
    __slots__ = ()


UNSET: Final = UnsetValue()


@dataclass(frozen=True)
class CreateTaskCommand:
    title: str
    description: str | None = None
    due_date: date | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UpdateTaskCommand:
    title: str | None | UnsetValue = UNSET
    description: str | None | UnsetValue = UNSET
    due_date: date | None | UnsetValue = UNSET
    tags: tuple[str, ...] | None | UnsetValue = UNSET

