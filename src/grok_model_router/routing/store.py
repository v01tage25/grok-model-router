from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class RouteConflict(RuntimeError):
    """The route changed since the caller last read it."""


@dataclass(frozen=True)
class RouteState:
    agent_id: str
    provider_id: str
    model_id: str
    paused: bool
    epoch: int
    parameters: dict[str, str]


class RouteStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS routes (
                    agent_id TEXT PRIMARY KEY,
                    provider_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    paused INTEGER NOT NULL,
                    epoch INTEGER NOT NULL,
                    parameters_json TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _validate_agent_id(agent_id: str) -> None:
        try:
            uuid.UUID(agent_id)
        except (ValueError, AttributeError, TypeError):
            raise ValueError("agent_id must be a UUID") from None

    @staticmethod
    def _validate_route(provider_id: str, model_id: str, parameters: Mapping[str, str]) -> dict[str, str]:
        if not provider_id.strip() or not model_id.strip():
            raise ValueError("provider_id and model_id are required")
        safe: dict[str, str] = {}
        for key, value in parameters.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("route parameters must be string pairs")
            if any(word in key.lower() for word in ("key", "token", "secret", "password", "credential")):
                raise ValueError("credential-like route parameters are not allowed")
            safe[key] = value
        return safe

    @staticmethod
    def _from_row(row: sqlite3.Row) -> RouteState:
        return RouteState(
            agent_id=row["agent_id"],
            provider_id=row["provider_id"],
            model_id=row["model_id"],
            paused=bool(row["paused"]),
            epoch=int(row["epoch"]),
            parameters=json.loads(row["parameters_json"]),
        )

    def get_route(self, agent_id: str) -> RouteState | None:
        self._validate_agent_id(agent_id)
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM routes WHERE agent_id = ?", (agent_id,)).fetchone()
        return None if row is None else self._from_row(row)

    def set_route(
        self,
        agent_id: str,
        provider_id: str,
        model_id: str,
        *,
        parameters: Mapping[str, str] | None = None,
        expected_epoch: int | None = None,
    ) -> RouteState:
        self._validate_agent_id(agent_id)
        safe_parameters = self._validate_route(provider_id, model_id, parameters or {})
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM routes WHERE agent_id = ?", (agent_id,)).fetchone()
            if row is None:
                if expected_epoch not in (None, 0):
                    raise RouteConflict("route does not exist at the expected epoch")
                epoch = 1
                connection.execute(
                    "INSERT INTO routes VALUES (?, ?, ?, 0, ?, ?)",
                    (agent_id, provider_id, model_id, epoch, json.dumps(safe_parameters, sort_keys=True)),
                )
            else:
                current = int(row["epoch"])
                if expected_epoch != current:
                    raise RouteConflict(f"expected epoch {expected_epoch}, current epoch {current}")
                epoch = current + 1
                connection.execute(
                    "UPDATE routes SET provider_id=?, model_id=?, paused=0, epoch=?, parameters_json=? WHERE agent_id=?",
                    (provider_id, model_id, epoch, json.dumps(safe_parameters, sort_keys=True), agent_id),
                )
            updated = connection.execute("SELECT * FROM routes WHERE agent_id = ?", (agent_id,)).fetchone()
        return self._from_row(updated)

    def _set_paused(self, agent_id: str, paused: bool, expected_epoch: int | None) -> RouteState:
        self._validate_agent_id(agent_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM routes WHERE agent_id = ?", (agent_id,)).fetchone()
            if row is None:
                raise RouteConflict("route does not exist")
            current = int(row["epoch"])
            if expected_epoch != current:
                raise RouteConflict(f"expected epoch {expected_epoch}, current epoch {current}")
            connection.execute(
                "UPDATE routes SET paused=?, epoch=? WHERE agent_id=?",
                (int(paused), current + 1, agent_id),
            )
            updated = connection.execute("SELECT * FROM routes WHERE agent_id = ?", (agent_id,)).fetchone()
        return self._from_row(updated)

    def pause(self, agent_id: str, *, expected_epoch: int) -> RouteState:
        return self._set_paused(agent_id, True, expected_epoch)

    def resume(self, agent_id: str, *, expected_epoch: int) -> RouteState:
        return self._set_paused(agent_id, False, expected_epoch)
