import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> FastAPI:
    return create_app(tmp_path / "test.db")


def graphql(client: FastAPI, query: str, variables: dict | None = None) -> dict:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=client)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http_client:
            return await http_client.post(
                "/graphql", json={"query": query, "variables": variables}
            )

    response = asyncio.run(send_request())
    assert response.status_code == 200
    return response.json()


def test_complete_task_lifecycle(client: FastAPI) -> None:
    created = graphql(
        client,
        """
        mutation Create($input: CreateTaskInput!) {
          createTask(input: $input) {
            id title description dueDate status tags { id name }
          }
        }
        """,
        {
            "input": {
                "title": "  Finish homework  ",
                "description": "Implement the GraphQL API",
                "dueDate": "2026-07-20",
                "tags": ["University", "graphql"],
            }
        },
    )
    assert "errors" not in created
    task = created["data"]["createTask"]
    assert task["title"] == "Finish homework"
    assert task["status"] == "TODO"
    assert {tag["name"] for tag in task["tags"]} == {"University", "graphql"}

    filtered = graphql(
        client,
        """
        query { tasks(status: TODO) { id title status } }
        """,
    )
    assert [item["id"] for item in filtered["data"]["tasks"]] == [task["id"]]

    changed = graphql(
        client,
        """
        mutation Change($id: ID!) {
          changeTaskStatus(id: $id, status: DOING) { id status }
        }
        """,
        {"id": task["id"]},
    )
    assert changed["data"]["changeTaskStatus"]["status"] == "DOING"

    updated = graphql(
        client,
        """
        mutation Update($id: ID!, $input: UpdateTaskInput!) {
          updateTask(id: $id, input: $input) {
            title description dueDate status tags { name }
          }
        }
        """,
        {
            "id": task["id"],
            "input": {"description": None, "dueDate": None, "tags": ["backend"]},
        },
    )
    updated_task = updated["data"]["updateTask"]
    assert updated_task["title"] == "Finish homework"
    assert updated_task["description"] is None
    assert updated_task["dueDate"] is None
    assert updated_task["status"] == "DOING"
    assert updated_task["tags"] == [{"name": "backend"}]

    deleted = graphql(
        client,
        "mutation Delete($id: ID!) { deleteTask(id: $id) }",
        {"id": task["id"]},
    )
    assert deleted["data"]["deleteTask"] is True

    fetched = graphql(
        client,
        "query One($id: ID!) { task(id: $id) { id } }",
        {"id": task["id"]},
    )
    assert fetched["data"]["task"] is None


def test_tag_is_reused_case_insensitively_and_can_filter(client: FastAPI) -> None:
    mutation = """
    mutation Create($input: CreateTaskInput!) {
      createTask(input: $input) { id tags { id name } }
    }
    """
    first = graphql(client, mutation, {"input": {"title": "One", "tags": ["API"]}})
    second = graphql(client, mutation, {"input": {"title": "Two", "tags": ["api"]}})
    first_tag = first["data"]["createTask"]["tags"][0]
    second_tag = second["data"]["createTask"]["tags"][0]
    assert first_tag == second_tag

    tags = graphql(client, "query { tags { id name tasks { title } } }")
    assert tags["data"]["tags"] == [
        {"id": first_tag["id"], "name": "API", "tasks": [{"title": "One"}, {"title": "Two"}]}
    ]

    tasks = graphql(
        client,
        "query Filter($tagId: ID) { tasks(tagId: $tagId) { title } }",
        {"tagId": first_tag["id"]},
    )
    assert [task["title"] for task in tasks["data"]["tasks"]] == ["One", "Two"]


def test_validation_and_not_found_errors(client: FastAPI) -> None:
    invalid = graphql(
        client,
        "mutation { createTask(input: {title: \"   \"}) { id } }",
    )
    assert invalid["data"] is None
    assert "title cannot be empty" in invalid["errors"][0]["message"]

    missing = graphql(
        client,
        "mutation { changeTaskStatus(id: \"999\", status: DONE) { id } }",
    )
    assert missing["data"] is None
    assert "was not found" in missing["errors"][0]["message"]
