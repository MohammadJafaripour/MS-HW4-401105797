from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.application.services import TaskService
from app.presentation.graphql.schema import schema


def create_http_app(task_service: TaskService) -> FastAPI:
    application = FastAPI(
        title="Mini Task Manager",
        description="A task management API implemented with Clean Architecture.",
        version="2.0.0",
    )
    application.state.task_service = task_service
    application.include_router(
        GraphQLRouter(schema, graphql_ide="graphiql"), prefix="/graphql"
    )

    @application.get("/health", tags=["System"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application

