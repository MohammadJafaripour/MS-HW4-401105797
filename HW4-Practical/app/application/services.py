from __future__ import annotations

from app.application.commands import (
    UNSET,
    CreateTaskCommand,
    UnsetValue,
    UpdateTaskCommand,
)
from app.application.ports import TaskRepository
from app.domain.entities import (
    Tag,
    Task,
    TaskStatus,
    normalize_description,
    normalize_tag_names,
    normalize_title,
)
from app.domain.exceptions import DomainValidationError, EntityNotFoundError


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    @staticmethod
    def _validate_id(entity_id: int, entity_name: str) -> int:
        if entity_id <= 0:
            raise DomainValidationError(
                f"{entity_name} ID must be a positive integer."
            )
        return entity_id

    def list_tasks(
        self, status: TaskStatus | None = None, tag_id: int | None = None
    ) -> list[Task]:
        if tag_id is not None:
            self._validate_id(tag_id, "Tag")
        return self.repository.list_tasks(status, tag_id)

    def get_task(self, task_id: int) -> Task | None:
        return self.repository.get_task(self._validate_id(task_id, "Task"))

    def list_tags(self) -> list[Tag]:
        return self.repository.list_tags()

    def get_tag(self, tag_id: int) -> Tag | None:
        return self.repository.get_tag(self._validate_id(tag_id, "Tag"))

    def create_task(self, command: CreateTaskCommand) -> Task:
        return self.repository.create_task(
            title=normalize_title(command.title),
            description=normalize_description(command.description),
            due_date=command.due_date,
            tag_names=normalize_tag_names(command.tags),
        )

    def update_task(self, task_id: int, command: UpdateTaskCommand) -> Task:
        task_id = self._validate_id(task_id, "Task")
        current = self.repository.get_task(task_id)
        if current is None:
            raise EntityNotFoundError(f"Task with ID {task_id} was not found.")

        title_value = current.title if command.title is UNSET else command.title
        description_value = (
            current.description
            if command.description is UNSET
            else command.description
        )
        due_date_value = (
            current.due_date if command.due_date is UNSET else command.due_date
        )
        tag_values = (
            tuple(tag.name for tag in current.tags)
            if command.tags is UNSET
            else command.tags or ()
        )

        assert not isinstance(title_value, UnsetValue)
        assert not isinstance(description_value, UnsetValue)
        assert not isinstance(due_date_value, UnsetValue)
        assert not isinstance(tag_values, UnsetValue)

        updated = self.repository.update_task(
            task_id=task_id,
            title=normalize_title(title_value),
            description=normalize_description(description_value),
            due_date=due_date_value,
            tag_names=normalize_tag_names(tag_values),
        )
        if updated is None:
            raise EntityNotFoundError(f"Task with ID {task_id} was not found.")
        return updated

    def change_task_status(self, task_id: int, status: TaskStatus) -> Task:
        task_id = self._validate_id(task_id, "Task")
        updated = self.repository.change_status(task_id, status)
        if updated is None:
            raise EntityNotFoundError(f"Task with ID {task_id} was not found.")
        return updated

    def delete_task(self, task_id: int) -> bool:
        task_id = self._validate_id(task_id, "Task")
        if not self.repository.delete_task(task_id):
            raise EntityNotFoundError(f"Task with ID {task_id} was not found.")
        return True

