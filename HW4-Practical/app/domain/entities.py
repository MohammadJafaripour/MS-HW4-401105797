from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable

from app.domain.exceptions import DomainValidationError


class TaskStatus(str, Enum):
    TODO = "TODO"
    DOING = "DOING"
    DONE = "DONE"


@dataclass(frozen=True)
class Tag:
    id: int
    name: str


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    description: str | None
    due_date: date | None
    status: TaskStatus
    tags: tuple[Tag, ...]


def normalize_title(value: str | None) -> str:
    if value is None or not value.strip():
        raise DomainValidationError("Task title cannot be empty.")
    title = value.strip()
    if len(title) > 200:
        raise DomainValidationError(
            "Task title cannot be longer than 200 characters."
        )
    return title


def normalize_description(value: str | None) -> str | None:
    if value is None:
        return None
    description = value.strip()
    return description or None


def normalize_tag_names(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw_name in values:
        name = raw_name.strip()
        if not name:
            raise DomainValidationError("Tag names cannot be empty.")
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            result.append(name)
    return tuple(result)

