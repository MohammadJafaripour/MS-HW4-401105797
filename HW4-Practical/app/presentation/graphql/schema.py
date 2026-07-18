from __future__ import annotations

from collections.abc import Callable
from datetime import date
from enum import Enum
from typing import Any, TypeVar

import strawberry
from graphql import GraphQLError
from starlette.concurrency import run_in_threadpool
from strawberry.types import Info

from app.application.commands import (
    UNSET,
    CreateTaskCommand,
    UpdateTaskCommand,
)
from app.application.services import TaskService
from app.domain.entities import (
    Tag as DomainTag,
    Task as DomainTask,
    TaskStatus as DomainTaskStatus,
)
from app.domain.exceptions import DomainValidationError, EntityNotFoundError


ResultType = TypeVar("ResultType")


@strawberry.enum(name="TaskStatus")
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
        records = await _run(
            _service(info).list_tasks, None, _parse_id(self.id, "Tag")
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


def _service(info: Info) -> TaskService:
    return info.context["request"].app.state.task_service


async def _run(
    use_case: Callable[..., ResultType], *args: Any
) -> ResultType:
    try:
        return await run_in_threadpool(use_case, *args)
    except (DomainValidationError, EntityNotFoundError) as error:
        raise GraphQLError(str(error)) from error


def _parse_id(value: strawberry.ID, entity_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise GraphQLError(
            f"{entity_name} ID must be a positive integer."
        ) from error


def _to_tag(entity: DomainTag) -> Tag:
    return Tag(id=strawberry.ID(str(entity.id)), name=entity.name)


def _to_task(entity: DomainTask) -> Task:
    return Task(
        id=strawberry.ID(str(entity.id)),
        title=entity.title,
        description=entity.description,
        due_date=entity.due_date,
        status=TaskStatus(entity.status.value),
        tags=[_to_tag(tag) for tag in entity.tags],
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
        records = await _run(
            _service(info).list_tasks,
            DomainTaskStatus(status.value) if status else None,
            parsed_tag_id,
        )
        return [_to_task(record) for record in records]

    @strawberry.field
    async def task(self, info: Info, id: strawberry.ID) -> Task | None:
        entity = await _run(_service(info).get_task, _parse_id(id, "Task"))
        return _to_task(entity) if entity else None

    @strawberry.field
    async def tags(self, info: Info) -> list[Tag]:
        entities = await _run(_service(info).list_tags)
        return [_to_tag(entity) for entity in entities]

    @strawberry.field
    async def tag(self, info: Info, id: strawberry.ID) -> Tag | None:
        entity = await _run(_service(info).get_tag, _parse_id(id, "Tag"))
        return _to_tag(entity) if entity else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_task(self, info: Info, input: CreateTaskInput) -> Task:
        entity = await _run(
            _service(info).create_task,
            CreateTaskCommand(
                title=input.title,
                description=input.description,
                due_date=input.due_date,
                tags=tuple(input.tags),
            ),
        )
        return _to_task(entity)

    @strawberry.mutation
    async def update_task(
        self, info: Info, id: strawberry.ID, input: UpdateTaskInput
    ) -> Task:
        tags = (
            UNSET
            if input.tags is strawberry.UNSET
            else tuple(input.tags) if input.tags is not None else None
        )
        entity = await _run(
            _service(info).update_task,
            _parse_id(id, "Task"),
            UpdateTaskCommand(
                title=UNSET if input.title is strawberry.UNSET else input.title,
                description=(
                    UNSET
                    if input.description is strawberry.UNSET
                    else input.description
                ),
                due_date=(
                    UNSET if input.due_date is strawberry.UNSET else input.due_date
                ),
                tags=tags,
            ),
        )
        return _to_task(entity)

    @strawberry.mutation
    async def change_task_status(
        self, info: Info, id: strawberry.ID, status: TaskStatus
    ) -> Task:
        entity = await _run(
            _service(info).change_task_status,
            _parse_id(id, "Task"),
            DomainTaskStatus(status.value),
        )
        return _to_task(entity)

    @strawberry.mutation
    async def delete_task(self, info: Info, id: strawberry.ID) -> bool:
        return await _run(_service(info).delete_task, _parse_id(id, "Task"))


schema = strawberry.Schema(query=Query, mutation=Mutation)

