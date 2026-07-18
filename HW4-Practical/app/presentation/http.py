from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse
from strawberry.fastapi import GraphQLRouter

from app.application.services import TaskService
from app.presentation.graphql.schema import schema


def create_http_app(task_service: TaskService, swagger_file: Path) -> FastAPI:
    application = FastAPI(
        title="Mini Task Manager",
        description="A task management API implemented with Clean Architecture.",
        version="2.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.task_service = task_service
    application.include_router(
        GraphQLRouter(schema, graphql_ide="graphiql"), prefix="/graphql"
    )

    @application.get("/health", tags=["System"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/swagger.yaml", include_in_schema=False)
    async def swagger_specification() -> FileResponse:
        return FileResponse(swagger_file, media_type="application/yaml")

    @application.get("/swagger", include_in_schema=False)
    @application.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/swagger.yaml",
            title="Mini Task Manager - Swagger UI",
        )

    return application
