import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import FastAPI
from openapi_spec_validator import validate

from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SWAGGER_FILE = PROJECT_ROOT / "swagger.yaml"


def _load_specification() -> dict[str, Any]:
    return yaml.safe_load(SWAGGER_FILE.read_text(encoding="utf-8"))


def _references(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            yield reference
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _resolve_local_reference(specification: dict[str, Any], reference: str) -> Any:
    assert reference.startswith("#/"), f"External reference is not expected: {reference}"
    current: Any = specification
    for segment in reference[2:].split("/"):
        current = current[segment.replace("~1", "/").replace("~0", "~")]
    return current


def _request(
    application: FastAPI,
    method: str,
    path: str,
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, json=json)

    return asyncio.run(send())


def test_swagger_file_has_required_openapi_structure_and_valid_references() -> None:
    specification = _load_specification()
    validate(specification)

    assert specification["openapi"] == "3.1.0"
    assert specification["info"]["title"] == "Mini Task Manager GraphQL API"
    assert {"/health", "/graphql"} <= specification["paths"].keys()

    graphql_operation = specification["paths"]["/graphql"]["post"]
    assert graphql_operation["operationId"] == "executeGraphQL"
    assert graphql_operation["requestBody"]["required"] is True
    assert "200" in graphql_operation["responses"]

    examples = graphql_operation["requestBody"]["content"]["application/json"][
        "examples"
    ]
    assert {
        "createTask",
        "listTasks",
        "getTask",
        "updateTask",
        "changeTaskStatus",
        "deleteTask",
        "listTags",
    } <= examples.keys()
    for example in examples.values():
        request = example["value"]
        assert request["operationName"] in request["query"]
        assert isinstance(request["variables"], dict)

    for reference in _references(specification):
        assert _resolve_local_reference(specification, reference) is not None


def test_swagger_file_and_ui_are_served_by_application(tmp_path: Path) -> None:
    application = create_app(tmp_path / "swagger-routes.db")

    specification_response = _request(application, "GET", "/swagger.yaml")
    assert specification_response.status_code == 200
    assert specification_response.headers["content-type"].startswith(
        "application/yaml"
    )
    assert yaml.safe_load(specification_response.text) == _load_specification()

    for path in ("/swagger", "/docs"):
        ui_response = _request(application, "GET", path)
        assert ui_response.status_code == 200
        assert "/swagger.yaml" in ui_response.text
        assert "Swagger UI" in ui_response.text


def test_documented_graphql_examples_execute_as_a_complete_workflow(
    tmp_path: Path,
) -> None:
    application = create_app(tmp_path / "swagger-examples.db")
    specification = _load_specification()
    examples = specification["paths"]["/graphql"]["post"]["requestBody"][
        "content"
    ]["application/json"]["examples"]

    workflow = (
        "createTask",
        "listTasks",
        "getTask",
        "updateTask",
        "changeTaskStatus",
        "listTags",
        "deleteTask",
    )
    results: dict[str, dict[str, Any]] = {}
    for example_name in workflow:
        response = _request(
            application,
            "POST",
            "/graphql",
            json=examples[example_name]["value"],
        )
        assert response.status_code == 200
        result = response.json()
        assert "errors" not in result, f"{example_name}: {result.get('errors')}"
        results[example_name] = result["data"]

    assert results["createTask"]["createTask"]["status"] == "TODO"
    assert len(results["listTasks"]["tasks"]) == 1
    assert results["getTask"]["task"]["id"] == "1"
    assert results["updateTask"]["updateTask"]["description"] == (
        "Final documented implementation"
    )
    assert results["changeTaskStatus"]["changeTaskStatus"]["status"] == "DONE"
    assert len(results["listTags"]["tags"]) == 3
    assert results["deleteTask"]["deleteTask"] is True
