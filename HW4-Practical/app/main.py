from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.database import TaskRepository
from app.schema import schema


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(database_path: str | Path | None = None) -> FastAPI:
    selected_path = database_path or os.getenv(
        "TASK_MANAGER_DB_PATH", str(PROJECT_ROOT / "task_manager.db")
    )
    repository = TaskRepository(selected_path)
    repository.initialize()

    application = FastAPI(
        title="Mini Task Manager",
        description="A task management API implemented with GraphQL and SQLite.",
        version="1.0.0",
    )
    application.state.repository = repository
    application.include_router(
        GraphQLRouter(schema, graphql_ide="graphiql"), prefix="/graphql"
    )

    @application.get("/health", tags=["System"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()

