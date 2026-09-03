"""Revision-preserving DB-API persistence for economic models and snapshots."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from economic_model import EconomicModel


MIGRATION = Path(__file__).with_name("migrations") / "economics" / "001_tweco_model_store.sql"


class EconomicModelRepository:
    def __init__(self, connection: Any):
        self.connection = connection
        module = type(connection).__module__.lower()
        self.placeholder = "?" if module.startswith("sqlite3") else "%s"

    def _sql(self, statement: str) -> str:
        return statement if self.placeholder == "?" else statement.replace("?", "%s")

    def migrate(self) -> None:
        sql = MIGRATION.read_text(encoding="utf-8")
        if hasattr(self.connection, "executescript"):
            self.connection.executescript(sql)
        else:
            cursor = self.connection.cursor()
            for statement in sql.split(";"):
                if statement.strip(): cursor.execute(statement)
        self.connection.commit()

    def save(self, model: EconomicModel, *, actor: str, reason: str) -> int:
        cursor = self.connection.cursor()
        cursor.execute(self._sql("SELECT COALESCE(MAX(revision), 0) FROM tweco_model_revisions WHERE model_id = ?"), (model.model_id,))
        revision = int(cursor.fetchone()[0]) + 1
        model.revision = revision
        model._audit(actor, "economic_model", model.model_id, "save", revision - 1, revision, reason)
        payload = json.dumps(model.to_document(), sort_keys=True, separators=(",", ":"))
        cursor.execute(
            self._sql("INSERT INTO tweco_model_revisions (model_id, project_id, revision, contract_version, payload, created_at, created_by, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"),
            (model.model_id, model.project_id, revision, "1.0", payload, datetime.now(timezone.utc).isoformat(), actor, reason),
        )
        self.connection.commit()
        return revision

    def load(self, model_id: str, revision: int | None = None) -> EconomicModel:
        cursor = self.connection.cursor()
        if revision is None:
            cursor.execute(self._sql("SELECT payload FROM tweco_model_revisions WHERE model_id = ? ORDER BY revision DESC LIMIT 1"), (model_id,))
        else:
            cursor.execute(self._sql("SELECT payload FROM tweco_model_revisions WHERE model_id = ? AND revision = ?"), (model_id, revision))
        row = cursor.fetchone()
        if not row: raise KeyError(f"Economic model revision not found: {model_id}/{revision or 'latest'}")
        return EconomicModel.from_document(json.loads(row[0]))

    def save_snapshot(self, model: EconomicModel, scenario_id: str = "base") -> dict[str, Any]:
        snapshot = model.snapshot(scenario_id)
        self.connection.execute(
            self._sql("INSERT INTO tweco_calculation_snapshots (snapshot_id, model_id, revision, scenario_id, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)"),
            (snapshot["snapshot_id"], model.model_id, model.revision, scenario_id,
             json.dumps(snapshot, sort_keys=True, separators=(",", ":")), snapshot["created_at"]),
        )
        self.connection.commit()
        return snapshot
