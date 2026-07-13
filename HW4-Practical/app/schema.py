from __future__ import annotations

from datetime import date
from enum import Enum

import strawberry
from graphql import GraphQLError
from starlette.concurrency import run_in_threadpool
from strawberry.types import Info

from app.database import TagRecord, TaskRecord, TaskRepository


@strawberry.enum
class TaskStatus(Enum):
    TODO = "TODO"
    DOING = "DOING"
    DONE = "DONE"


@strawberry.type
class Tag:
    id: strawberry.ID
    name: str

    @strawberry.field
    async def tasks(self, info: Info) -> list[Task]:
        records = await run_in_threadpool(
            _repository(info).list_tasks, None, _parse_id(self.id, "Tag")
        )
        return [_to_task(record) for record in records]


@strawberry.type
class Task:
    id: strawberry.ID
    title: str
    description: str | None
    due_date: date | None
    status: TaskStatus
    tags: list[Tag]


@strawberry.input
class CreateTaskInput:
    title: str
    description: str | None = None
    due_date: date | None = None
    tags: list[str] = strawberry.field(default_factory=list)


@strawberry.input
class UpdateTaskInput:
    title: str | None = strawberry.UNSET
    description: str | None = strawberry.UNSET
    due_date: date | None = strawberry.UNSET
    tags: list[str] | None = strawberry.UNSET


def _repository(info: Info) -> TaskRepository:
    return info.context["request"].app.state.repository


def _parse_id(value: strawberry.ID, entity_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise GraphQLError(f"{entity_name} ID must be a positive integer.") from error
    if parsed <= 0:
        raise GraphQLError(f"{entity_name} ID must be a positive integer.")
    return parsed


def _clean_title(value: str | None) -> str:
    if value is None or not value.strip():
        raise GraphQLError("Task title cannot be empty.")
    title = value.strip()
    if len(title) > 200:
        raise GraphQLError("Task title cannot be longer than 200 characters.")
    return title


def _clean_description(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _to_tag(record: TagRecord) -> Tag:
    return Tag(id=strawberry.ID(str(record.id)), name=record.name)


def _to_task(record: TaskRecord) -> Task:
    return Task(
        id=strawberry.ID(str(record.id)),
        title=record.title,
        description=record.description,
        due_date=date.fromisoformat(record.due_date) if record.due_date else None,
        status=TaskStatus(record.status),
        tags=[_to_tag(tag) for tag in record.tags],
    )


@strawberry.type
class Query:
    @strawberry.field
    async def tasks(
        self,
        info: Info,
        status: TaskStatus | None = None,
        tag_id: strawberry.ID | None = None,
    ) -> list[Task]:
        parsed_tag_id = _parse_id(tag_id, "Tag") if tag_id is not None else None
        records = await run_in_threadpool(
            _repository(info).list_tasks,
            status.value if status else None,
            parsed_tag_id,
        )
        return [_to_task(record) for record in records]

    @strawberry.field
    async def task(self, info: Info, id: strawberry.ID) -> Task | None:
        record = await run_in_threadpool(
            _repository(info).get_task, _parse_id(id, "Task")
        )
        return _to_task(record) if record else None

    @strawberry.field
    async def tags(self, info: Info) -> list[Tag]:
        records = await run_in_threadpool(_repository(info).list_tags)
        return [_to_tag(record) for record in records]

    @strawberry.field
    async def tag(self, info: Info, id: strawberry.ID) -> Tag | None:
        record = await run_in_threadpool(
            _repository(info).get_tag, _parse_id(id, "Tag")
        )
        return _to_tag(record) if record else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_task(self, info: Info, input: CreateTaskInput) -> Task:
        try:
            record = await run_in_threadpool(
                _repository(info).create_task,
                _clean_title(input.title),
                _clean_description(input.description),
                input.due_date.isoformat() if input.due_date else None,
                input.tags,
            )
        except ValueError as error:
            raise GraphQLError(str(error)) from error
        return _to_task(record)

    @strawberry.mutation
    async def update_task(
        self, info: Info, id: strawberry.ID, input: UpdateTaskInput
    ) -> Task:
        task_id = _parse_id(id, "Task")
        repository = _repository(info)
        current = await run_in_threadpool(repository.get_task, task_id)
        if current is None:
            raise GraphQLError(f"Task with ID {task_id} was not found.")

        title = current.title if input.title is strawberry.UNSET else input.title
        description = (
            current.description
            if input.description is strawberry.UNSET
            else input.description
        )
        due_date = (
            current.due_date
            if input.due_date is strawberry.UNSET
            else input.due_date.isoformat() if input.due_date else None
        )
        tags = (
            [tag.name for tag in current.tags]
            if input.tags is strawberry.UNSET
            else input.tags or []
        )

        try:
            record = await run_in_threadpool(
                repository.update_task,
                task_id,
                _clean_title(title),
                _clean_description(description),
                due_date,
                tags,
            )
        except ValueError as error:
            raise GraphQLError(str(error)) from error
        if record is None:
            raise GraphQLError(f"Task with ID {task_id} was not found.")
        return _to_task(record)

    @strawberry.mutation
    async def change_task_status(
        self, info: Info, id: strawberry.ID, status: TaskStatus
    ) -> Task:
        task_id = _parse_id(id, "Task")
        record = await run_in_threadpool(
            _repository(info).change_status, task_id, status.value
        )
        if record is None:
            raise GraphQLError(f"Task with ID {task_id} was not found.")
        return _to_task(record)

    @strawberry.mutation
    async def delete_task(self, info: Info, id: strawberry.ID) -> bool:
        task_id = _parse_id(id, "Task")
        deleted = await run_in_threadpool(_repository(info).delete_task, task_id)
        if not deleted:
            raise GraphQLError(f"Task with ID {task_id} was not found.")
        return True


schema = strawberry.Schema(query=Query, mutation=Mutation)
