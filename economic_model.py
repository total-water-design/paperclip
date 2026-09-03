"""Auditable model rows, scenario inheritance, provenance and snapshots."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import uuid
from typing import Any

from economic_formula_graph import evaluate_graph
from economic_model_contracts import contract_header, validate_contract


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


@dataclass
class ModelRow:
    row_id: str
    description: str
    category: str
    value: float | None = None
    formula: str = ""
    wbs_id: str = ""
    quantity: float | None = None
    unit: str = ""
    unit_cost: float | None = None
    native_currency: str = "USD"
    reporting_currency: str = "USD"
    base_date: str = ""
    timing_start: str = ""
    timing_end: str = ""
    escalation_profile_id: str = ""
    fx_snapshot_id: str = ""
    source_type: str = "user"
    source_reference: str = ""
    source_lineage_id: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.row_id: raise ValueError("Model rows require a stable row_id.")
        if bool(self.formula) == (self.value is not None):
            raise ValueError(f"Row {self.row_id} must define exactly one of value or formula.")
        if self.native_currency != self.reporting_currency and not self.fx_snapshot_id:
            raise ValueError(f"Row {self.row_id} requires an FX snapshot for cross-currency use.")


@dataclass
class Scenario:
    scenario_id: str
    name: str
    parent_id: str | None = None
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


class EconomicModel:
    def __init__(self, project_id: str, name: str, *, reporting_currency: str = "USD", model_id: str | None = None):
        self.model_id, self.project_id, self.name = model_id or _id(), project_id, name
        self.reporting_currency = reporting_currency
        self.revision = 0
        self.rows: dict[str, ModelRow] = {}
        self.scenarios: dict[str, Scenario] = {"base": Scenario("base", "Base")}
        self.lineage: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []

    def _audit(self, actor: str, entity: str, entity_id: str, action: str, before: Any, after: Any, reason: str) -> None:
        self.audit_events.append({
            "event_id": _id(), "timestamp": _now(), "actor": actor,
            "project_revision": self.revision, "entity": entity, "entity_id": entity_id,
            "action": action, "previous": deepcopy(before), "new": deepcopy(after), "reason": reason,
        })

    def add_lineage(self, source_type: str, reference: str, *, actor: str, metadata: dict | None = None) -> str:
        lineage_id = _id()
        record = {"lineage_id": lineage_id, "source_type": source_type, "reference": reference,
                  "metadata": deepcopy(metadata or {}), "captured_at": _now()}
        self.lineage[lineage_id] = record
        self._audit(actor, "source_lineage", lineage_id, "create", None, record, "Source captured")
        return lineage_id

    def upsert_row(self, row: ModelRow, *, actor: str, reason: str) -> None:
        if row.source_lineage_id and row.source_lineage_id not in self.lineage:
            raise ValueError(f"Unknown source lineage: {row.source_lineage_id}")
        before = asdict(self.rows[row.row_id]) if row.row_id in self.rows else None
        self.rows[row.row_id] = deepcopy(row)
        self._audit(actor, "model_row", row.row_id, "update" if before else "create", before, asdict(row), reason)

    def add_scenario(self, scenario: Scenario, *, actor: str, reason: str) -> None:
        if scenario.scenario_id == "base" or scenario.scenario_id in self.scenarios:
            raise ValueError(f"Scenario already exists: {scenario.scenario_id}")
        if scenario.parent_id not in self.scenarios:
            raise ValueError(f"Unknown parent scenario: {scenario.parent_id}")
        self.scenarios[scenario.scenario_id] = deepcopy(scenario)
        self._audit(actor, "scenario", scenario.scenario_id, "create", None, asdict(scenario), reason)

    def set_override(self, scenario_id: str, row_id: str, change: dict[str, Any], *, actor: str, reason: str) -> None:
        if scenario_id == "base" or scenario_id not in self.scenarios: raise ValueError("Overrides require a non-base scenario.")
        if row_id not in self.rows: raise ValueError(f"Unknown model row: {row_id}")
        allowed = {"value", "formula", "notes", "source_lineage_id"}
        if not change or set(change) - allowed: raise ValueError("Scenario override contains unsupported fields.")
        candidate = asdict(self.rows[row_id])
        candidate.update(deepcopy(change))
        ModelRow(**candidate)
        lineage_id = candidate.get("source_lineage_id")
        if lineage_id and lineage_id not in self.lineage:
            raise ValueError(f"Unknown source lineage: {lineage_id}")
        before = self.scenarios[scenario_id].overrides.get(row_id)
        self.scenarios[scenario_id].overrides[row_id] = deepcopy(change)
        self._audit(actor, "scenario_override", f"{scenario_id}:{row_id}", "override", before, change, reason)

    def revert_override(self, scenario_id: str, row_id: str, *, actor: str, reason: str) -> None:
        before = self.scenarios[scenario_id].overrides.pop(row_id, None)
        self._audit(actor, "scenario_override", f"{scenario_id}:{row_id}", "revert", before, None, reason)

    def resolved_rows(self, scenario_id: str = "base") -> dict[str, dict[str, Any]]:
        if scenario_id not in self.scenarios: raise ValueError(f"Unknown scenario: {scenario_id}")
        chain: list[Scenario] = []
        cursor: str | None = scenario_id
        seen: set[str] = set()
        while cursor:
            if cursor in seen: raise ValueError("Circular scenario inheritance.")
            seen.add(cursor); scenario = self.scenarios[cursor]; chain.append(scenario); cursor = scenario.parent_id
        resolved = {key: asdict(value) for key, value in self.rows.items()}
        for scenario in reversed(chain):
            for row_id, change in scenario.overrides.items(): resolved[row_id].update(deepcopy(change))
        for row in resolved.values():
            ModelRow(**row)
        return resolved

    def calculate(self, scenario_id: str = "base") -> dict[str, float]:
        return evaluate_graph(self.resolved_rows(scenario_id))

    def to_document(self) -> dict[str, Any]:
        return {**contract_header("twds.economic_model"), "model_id": self.model_id,
                "project_id": self.project_id, "name": self.name, "reporting_currency": self.reporting_currency,
                "revision": self.revision, "rows": [asdict(row) for row in self.rows.values()],
                "scenarios": [asdict(scenario) for scenario in self.scenarios.values()],
                "source_lineage": list(self.lineage.values()), "audit_events": deepcopy(self.audit_events)}

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "EconomicModel":
        data = validate_contract(document, "twds.economic_model")
        model = cls(data["project_id"], data["name"], reporting_currency=data["reporting_currency"], model_id=data["model_id"])
        model.revision = int(data.get("revision", 0))
        model.rows = {item["row_id"]: ModelRow(**item) for item in data.get("rows", [])}
        model.scenarios = {item["scenario_id"]: Scenario(**item) for item in data.get("scenarios", [])}
        if "base" not in model.scenarios: raise ValueError("Economic model requires a base scenario.")
        model.lineage = {item["lineage_id"]: item for item in data.get("source_lineage", [])}
        model.audit_events = deepcopy(data.get("audit_events", []))
        return model

    def snapshot(self, scenario_id: str = "base") -> dict[str, Any]:
        payload = {"model": self.to_document(), "scenario_id": scenario_id, "results": self.calculate(scenario_id)}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return {"snapshot_id": hashlib.sha256(canonical.encode()).hexdigest(), "created_at": _now(), **payload}
