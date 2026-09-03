import sqlite3

import pytest

from economic_formula_graph import (
    CircularReferenceError,
    FormulaSecurityError,
    MissingReferenceError,
    compile_formula,
    evaluate_formula,
    evaluate_graph,
)
from economic_model import EconomicModel, ModelRow, Scenario
from economic_model_contracts import ContractError, contract_header, validate_contract
from economic_persistence import EconomicModelRepository


def test_versioned_contract_rejects_unknown_and_stale_documents():
    assert contract_header("twds.economic_model") == {
        "contract_id": "twds.economic_model",
        "contract_version": "1.0",
    }
    with pytest.raises(ContractError, match="Unknown TWDS contract"):
        contract_header("twds.unknown")
    with pytest.raises(ContractError, match="Unsupported"):
        validate_contract({"contract_id": "twds.economic_model", "contract_version": "0.9"})


def test_controlled_formula_graph_evaluates_dependencies_and_blocks_code():
    rows = {
        "quantity": {"value": 3.0},
        "unit_cost": {"value": 7.0},
        "installed": {"formula": '=REF("quantity") * unit_cost'},
        "total": {"formula": "SUM(installed, 4)"},
    }
    assert evaluate_graph(rows) == {
        "quantity": 3.0,
        "unit_cost": 7.0,
        "installed": 21.0,
        "total": 25.0,
    }
    with pytest.raises(FormulaSecurityError):
        compile_formula('__import__("os").system("id")')
    with pytest.raises(FormulaSecurityError, match="exponent"):
        evaluate_formula("9 ** 999999", {})


def test_formula_graph_reports_missing_and_circular_stable_row_references():
    with pytest.raises(MissingReferenceError, match="deleted"):
        evaluate_graph({"total": {"formula": "REF('removed-row')"}})
    with pytest.raises(CircularReferenceError, match="a depends on b depends on a"):
        evaluate_graph({"a": {"formula": "b + 1"}, "b": {"formula": "a + 1"}})


def _model():
    model = EconomicModel("project-7", "Lifecycle model")
    lineage = model.add_lineage(
        "vendor_quote", "quote-17.pdf", actor="estimator@example.com", metadata={"page": 3}
    )
    model.upsert_row(
        ModelRow("equipment", "Equipment", "capex", value=100.0, source_lineage_id=lineage),
        actor="estimator@example.com",
        reason="Vendor quote received",
    )
    model.upsert_row(
        ModelRow("installed", "Installed", "capex", formula="equipment * 1.25"),
        actor="estimator@example.com",
        reason="Apply installation factor",
    )
    return model


def test_scenario_inheritance_provenance_audit_and_revert():
    model = _model()
    model.add_scenario(Scenario("high", "High", "base"), actor="analyst", reason="Sensitivity")
    model.add_scenario(Scenario("stress", "Stress", "high"), actor="analyst", reason="Sensitivity")
    model.set_override("high", "equipment", {"value": 120.0}, actor="analyst", reason="High quote")
    assert model.calculate("stress") == {"equipment": 120.0, "installed": 150.0}
    model.revert_override("high", "equipment", actor="analyst", reason="Revert to inherited value")
    assert model.calculate("stress") == {"equipment": 100.0, "installed": 125.0}
    assert model.audit_events[-1]["action"] == "revert"
    assert model.lineage[next(iter(model.lineage))]["reference"] == "quote-17.pdf"


def test_invalid_scenario_override_cannot_create_value_and_formula():
    model = _model()
    model.add_scenario(Scenario("high", "High", "base"), actor="analyst", reason="Sensitivity")
    with pytest.raises(ValueError, match="exactly one"):
        model.set_override("high", "equipment", {"formula": "2 + 2"}, actor="analyst", reason="Invalid")


def test_sqlite_migration_revision_history_round_trip_and_snapshot():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    repository = EconomicModelRepository(connection)
    repository.migrate()
    model = _model()
    assert repository.save(model, actor="estimator", reason="Initial issue") == 1
    model.rows["equipment"].value = 110.0
    assert repository.save(model, actor="estimator", reason="Quote revision") == 2
    assert repository.load(model.model_id, 1).calculate()["installed"] == 125.0
    assert repository.load(model.model_id).calculate()["installed"] == 137.5
    snapshot = repository.save_snapshot(model)
    assert snapshot["results"] == {"equipment": 110.0, "installed": 137.5}
    assert len(snapshot["snapshot_id"]) == 64


def test_postgres_connections_use_dbapi_format_placeholders():
    class FakePostgresConnection:
        pass

    FakePostgresConnection.__module__ = "psycopg.connection"
    repository = EconomicModelRepository(FakePostgresConnection())
    assert repository._sql("SELECT * FROM model WHERE id = ? AND revision = ?") == (
        "SELECT * FROM model WHERE id = %s AND revision = %s"
    )
