from __future__ import annotations

from datetime import date
from typing import Protocol

from app.domain.entities import Tag, Task, TaskStatus


class TaskRepository(Protocol):
    def get_task(self, task_id: int) -> Task | None: ...

    def list_tasks(
        self, status: TaskStatus | None = None, tag_id: int | None = None
    ) -> list[Task]: ...

    def list_tags(self) -> list[Tag]: ...

    def get_tag(self, tag_id: int) -> Tag | None: ...

    def create_task(
        self,
        title: str,
        description: str | None,
        due_date: date | None,
        tag_names: tuple[str, ...],
    ) -> Task: ...

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str | None,
        due_date: date | None,
        tag_names: tuple[str, ...],
    ) -> Task | None: ...

    def change_status(self, task_id: int, status: TaskStatus) -> Task | None: ...

    def delete_task(self, task_id: int) -> bool: ...

