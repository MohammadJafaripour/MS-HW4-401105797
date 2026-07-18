from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from app.application.services import TaskService
from app.infrastructure.sqlite_repository import SQLiteTaskRepository
from app.presentation.http import create_http_app


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(database_path: str | Path | None = None) -> FastAPI:
    selected_path = database_path or os.getenv(
        "TASK_MANAGER_DB_PATH", str(PROJECT_ROOT / "task_manager.db")
    )
    repository = SQLiteTaskRepository(selected_path)
    repository.initialize()
    return create_http_app(TaskService(repository), PROJECT_ROOT / "swagger.yaml")


app = create_app()
