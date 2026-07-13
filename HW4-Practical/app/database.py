from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class TagRecord:
    id: int
    name: str


@dataclass(frozen=True)
class TaskRecord:
    id: int
    title: str
    description: str | None
    due_date: str | None
    status: str
    tags: tuple[TagRecord, ...]


class TaskRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
                    description TEXT,
                    due_date TEXT,
                    status TEXT NOT NULL DEFAULT 'TODO'
                        CHECK (status IN ('TODO', 'DOING', 'DONE')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE
                        CHECK (length(trim(name)) > 0)
                );

                CREATE TABLE IF NOT EXISTS task_tags (
                    task_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (task_id, tag_id),
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_task_tags_tag_id ON task_tags(tag_id);
                """
            )

    @staticmethod
    def _normalize_tags(tag_names: Iterable[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for raw_name in tag_names:
            name = raw_name.strip()
            if not name:
                raise ValueError("Tag names cannot be empty.")
            key = name.casefold()
            if key not in seen:
                seen.add(key)
                result.append(name)
        return result

    @staticmethod
    def _tags_for_task(
        connection: sqlite3.Connection, task_id: int
    ) -> tuple[TagRecord, ...]:
        rows = connection.execute(
            """
            SELECT tags.id, tags.name
            FROM tags
            JOIN task_tags ON task_tags.tag_id = tags.id
            WHERE task_tags.task_id = ?
            ORDER BY tags.name COLLATE NOCASE
            """,
            (task_id,),
        ).fetchall()
        return tuple(TagRecord(id=row["id"], name=row["name"]) for row in rows)

    @classmethod
    def _task_from_row(
        cls, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> TaskRecord:
        return TaskRecord(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            due_date=row["due_date"],
            status=row["status"],
            tags=cls._tags_for_task(connection, row["id"]),
        )

    @staticmethod
    def _replace_tags(
        connection: sqlite3.Connection, task_id: int, tag_names: Iterable[str]
    ) -> None:
        connection.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))
        for name in TaskRepository._normalize_tags(tag_names):
            connection.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (name,))
            tag_row = connection.execute(
                "SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            connection.execute(
                "INSERT INTO task_tags(task_id, tag_id) VALUES (?, ?)",
                (task_id, tag_row["id"]),
            )

    def get_task(self, task_id: int) -> TaskRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, title, description, due_date, status FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            return self._task_from_row(connection, row) if row else None

    def list_tasks(
        self, status: str | None = None, tag_id: int | None = None
    ) -> list[TaskRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT t.id, t.title, t.description, t.due_date, t.status
                FROM tasks AS t
                LEFT JOIN task_tags AS tt ON tt.task_id = t.id
                WHERE (? IS NULL OR t.status = ?)
                  AND (? IS NULL OR tt.tag_id = ?)
                ORDER BY t.id
                """,
                (status, status, tag_id, tag_id),
            ).fetchall()
            return [self._task_from_row(connection, row) for row in rows]

    def list_tags(self) -> list[TagRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name FROM tags ORDER BY name COLLATE NOCASE"
            ).fetchall()
            return [TagRecord(id=row["id"], name=row["name"]) for row in rows]

    def get_tag(self, tag_id: int) -> TagRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name FROM tags WHERE id = ?", (tag_id,)
            ).fetchone()
            return TagRecord(id=row["id"], name=row["name"]) if row else None

    def create_task(
        self,
        title: str,
        description: str | None,
        due_date: str | None,
        tag_names: Iterable[str],
    ) -> TaskRecord:
        normalized_tags = self._normalize_tags(tag_names)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks(title, description, due_date, status)
                VALUES (?, ?, ?, 'TODO')
                """,
                (title, description, due_date),
            )
            task_id = cursor.lastrowid
            self._replace_tags(connection, task_id, normalized_tags)
        task = self.get_task(task_id)
        assert task is not None
        return task

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str | None,
        due_date: str | None,
        tag_names: Iterable[str],
    ) -> TaskRecord | None:
        normalized_tags = self._normalize_tags(tag_names)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, due_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (title, description, due_date, task_id),
            )
            if cursor.rowcount == 0:
                return None
            self._replace_tags(connection, task_id, normalized_tags)
        return self.get_task(task_id)

    def change_status(self, task_id: int, status: str) -> TaskRecord | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, task_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

