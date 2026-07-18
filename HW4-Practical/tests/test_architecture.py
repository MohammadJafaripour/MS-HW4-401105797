import ast
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.application.commands import CreateTaskCommand
from app.application.services import TaskService
from app.domain.entities import Task, TaskStatus
from app.domain.exceptions import DomainValidationError


APP_ROOT = Path(__file__).resolve().parent.parent / "app"


def _imported_modules(source_file: Path) -> set[str]:
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize(
    ("layer", "forbidden_prefixes"),
    [
        (
            "domain",
            (
                "app.application",
                "app.infrastructure",
                "app.presentation",
                "fastapi",
                "strawberry",
                "sqlite3",
            ),
        ),
        (
            "application",
            (
                "app.infrastructure",
                "app.presentation",
                "fastapi",
                "strawberry",
                "sqlite3",
            ),
        ),
    ],
)
def test_inner_layers_do_not_depend_on_outer_layers(
    layer: str, forbidden_prefixes: tuple[str, ...]
) -> None:
    for source_file in (APP_ROOT / layer).glob("*.py"):
        imports = _imported_modules(source_file)
        violations = {
            module
            for module in imports
            if module.startswith(forbidden_prefixes)
        }
        assert not violations, f"{source_file.name}: forbidden imports {violations}"


def test_create_use_case_normalizes_domain_data_without_frameworks() -> None:
    repository = Mock()
    expected = Task(
        id=1,
        title="Clean task",
        description=None,
        due_date=date(2026, 7, 20),
        status=TaskStatus.TODO,
        tags=(),
    )
    repository.create_task.return_value = expected
    service = TaskService(repository)

    result = service.create_task(
        CreateTaskCommand(
            title="  Clean task  ",
            description="   ",
            due_date=date(2026, 7, 20),
            tags=(" API ", "api"),
        )
    )

    assert result is expected
    repository.create_task.assert_called_once_with(
        title="Clean task",
        description=None,
        due_date=date(2026, 7, 20),
        tag_names=("API",),
    )


def test_invalid_domain_data_never_reaches_repository() -> None:
    repository = Mock()
    service = TaskService(repository)

    with pytest.raises(DomainValidationError, match="title cannot be empty"):
        service.create_task(CreateTaskCommand(title="   "))

    repository.create_task.assert_not_called()

