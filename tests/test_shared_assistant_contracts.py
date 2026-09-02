import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from contracts.assistant.v1 import (
    ContractValidationError,
    build_context_envelope,
    confirmation_request_digest,
    dispatch_tool,
    validate_action,
    validate_context_envelope,
)
from flowsheet import Stream


ROOT = Path(__file__).parents[1] / "contracts" / "assistant" / "v1"


def load(name):
    return json.loads((ROOT / name).read_text())


def test_contract_schemas_are_valid_draft_2020_12():
    for name in (
        "assistant-manifest.schema.json",
        "assistant-response.schema.json",
        "semantic-target-registry.schema.json",
        "tool-registration.schema.json",
        "context-envelope.schema.json",
        "tool-request.schema.json",
        "tool-result.schema.json",
    ):
        jsonschema.Draft202012Validator.check_schema(load(name))


def test_published_registries_and_manifest_match_authoritative_schemas():
    jsonschema.validate(load("manifest.example.json"), load("assistant-manifest.schema.json"))
    jsonschema.validate(load("semantic-targets.json"), load("semantic-target-registry.schema.json"))
    jsonschema.validate(load("tools.json"), load("tool-registration.schema.json"))


def test_structured_response_requires_provenance_and_confirmation_for_tools():
    response = {
        "contract": "twds.assistant.response/v1",
        "response_id": "response-1",
        "assistant_id": "twds.example.read-only",
        "message": "Review the calculation provenance.",
        "actions": [{
            "action_id": "action-1",
            "kind": "propose_tool",
            "tool_id": "ro.recalculate",
            "arguments": {},
            "label": "Recalculate",
            "requires_confirmation": True,
        }],
        "provenance": {
            "candidate_sha": "f" * 40,
            "context_refs": ["case:example"],
            "generated_at": "2026-09-01T00:00:00Z",
        },
    }
    jsonschema.validate(response, load("assistant-response.schema.json"))

    response["actions"][0]["requires_confirmation"] = False
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.validate(response, load("assistant-response.schema.json"))


def test_registry_ids_are_unique():
    targets = [item["target_id"] for item in load("semantic-targets.json")["targets"]]
    tools = [item["tool_id"] for item in load("tools.json")["tools"]]
    assert len(targets) == len(set(targets))
    assert len(tools) == len(set(tools))


def context(state="converged"):
    value = {
        "contract": "twds.assistant.context/v1", "context_id": "context-1",
        "source": {"application": "total-ro", "case_ref": "case:1", "candidate_sha": "a" * 40},
        "waterstream": {"water_state": {"pressure_bar": 55.0}, "streams": [{"name": "permeate"}]},
        "chemistry": {"composition": {"boron": 1.5}, "speciation": {"boron": {"H3BO3": 1.0}}},
        "mass_energy_balance": {"water_closure": 0.0, "component_closure": {"boron": 0.0}, "energy": {"kwh": 2.0}},
        "convergence": {"state": state, "iterations": 7, "residual_norm": 0.0001},
        "units": {"flow": "m3/h", "pressure": "bar"}, "handoff": {"state": "available", "target_application": "total-zld"},
    }
    if state != "converged":
        value["convergence"]["failure"] = {"code": "MAX_ITERATIONS", "message": "solver stopped"}
    return value


def request(state="converged"):
    value = {
        "contract": "twds.assistant.tool-request/v1", "request_id": "run-1", "tool_id": "ro.evaluate-boron",
        "arguments": {"report": True}, "context": context(state),
        "provenance": {"requested_by": "suite-core", "requested_at": "2026-09-01T00:00:00Z"},
    }
    value["confirmation"] = {
        "action_id": "action-1", "request_digest": confirmation_request_digest(value, "action-1"),
        "issued_at": "2026-09-01T00:00:00Z", "expires_at": "2026-09-01T00:05:00Z", "token": "signed-grant",
    }
    return value


NOW = datetime(2026, 9, 1, 0, 1, tzinfo=timezone.utc)


def verified(confirmation, binding):
    return confirmation["token"] == "signed-grant" and binding["action_id"] == "action-1"


REGISTRY = {"tools": [{"tool_id": "ro.evaluate-boron", "deterministic": True, "input_schema": {
    "type": "object", "additionalProperties": False, "required": ["report"], "properties": {"report": {"const": True}}
}, "output_schema": {"type": "object"}}]}


def test_context_envelope_serializes_cross_domain_state_and_requires_failure_details():
    validate_context_envelope(context())
    validate_context_envelope(context("non_converged"))
    failed = context("failed")
    del failed["convergence"]["failure"]
    with pytest.raises(ContractValidationError, match="failure"):
        validate_context_envelope(failed)


def test_context_builder_serializes_application_owned_waterstream_without_solver_calls():
    stream = Stream(2.5, pressure_bar=55.0, composition_mg_l={"boron": 1.5}, name="feed")
    envelope = build_context_envelope(
        context_id="context-1", source=context()["source"], water_state={"temperature_c": 25.0}, streams=[stream],
        composition={"boron": 1.5}, speciation={"boron": {"H3BO3": 1.0}},
        mass_energy_balance={"water_closure": 0.0, "component_closure": {"boron": 0.0}, "energy": {"kwh": 2.0}},
        convergence={"state": "converged", "iterations": 7}, units={"flow": "m3/h"}, handoff={"state": "none"},
    )
    assert envelope["waterstream"]["streams"][0]["name"] == "feed"


def test_dispatch_is_deterministic_and_requires_boron_provenance():
    def boron_handler(arguments, envelope):
        assert arguments == {"report": True}
        return {"output": {"boron_mg_l": envelope["chemistry"]["composition"]["boron"]}, "provenance": {
            "candidate_sha": "a" * 40, "context_id": envelope["context_id"], "tool_run_id": "tool-1",
            "boron_tool": {"status": "evaluated", "method": "speciation"},
        }}

    result = dispatch_tool(request(), REGISTRY, {"ro.evaluate-boron": boron_handler}, verified, now=NOW)
    assert result["status"] == "succeeded"
    assert result["output"] == {"boron_mg_l": 1.5}

    def missing_boron(arguments, envelope):
        return {"provenance": {"candidate_sha": "a" * 40, "context_id": envelope["context_id"], "tool_run_id": "tool-2"}}

    with pytest.raises(ContractValidationError, match="boron_tool"):
        dispatch_tool(request(), REGISTRY, {"ro.evaluate-boron": missing_boron}, verified, now=NOW)


def test_dispatch_rejects_handler_output_that_violates_registered_schema():
    def invalid_output_handler(arguments, envelope):
        return {"output": ["not-an-object"], "provenance": {
            "candidate_sha": "a" * 40, "context_id": envelope["context_id"], "tool_run_id": "tool-invalid",
            "boron_tool": {"status": "evaluated", "method": "speciation"},
        }}

    with pytest.raises(ContractValidationError, match="tool output:.*not of type 'object'"):
        dispatch_tool(request(), REGISTRY, {"ro.evaluate-boron": invalid_output_handler}, verified, now=NOW)


def test_nonconverged_tool_result_is_propagated_and_semantic_actions_must_resolve():
    def failed_handler(arguments, envelope):
        return {"status": "non_converged", "output": {}, "failure": {"code": "MAX_ITERATIONS", "message": "solver stopped"}, "provenance": {
            "candidate_sha": "a" * 40, "context_id": envelope["context_id"], "tool_run_id": "tool-3",
            "boron_tool": {"status": "unavailable"},
        }}

    assert dispatch_tool(request("non_converged"), REGISTRY, {"ro.evaluate-boron": failed_handler}, verified, now=NOW)["status"] == "non_converged"
    validate_action({"kind": "navigate", "target_id": "suite.home"}, load("semantic-targets.json"), REGISTRY)
    with pytest.raises(ContractValidationError, match="not registered"):
        validate_action({"kind": "propose_tool", "tool_id": "missing.tool", "requires_confirmation": True}, load("semantic-targets.json"), REGISTRY)


def test_dispatch_rejects_absent_or_malformed_confirmation_without_execution():
    calls = []
    handler = lambda arguments, envelope: calls.append(True)
    absent = request()
    del absent["confirmation"]
    with pytest.raises(ContractValidationError, match="confirmation.*required"):
        dispatch_tool(absent, REGISTRY, {"ro.evaluate-boron": handler}, verified, now=NOW)
    malformed = request()
    malformed["confirmation"]["request_digest"] = "not-a-digest"
    with pytest.raises(ContractValidationError, match="does not match"):
        dispatch_tool(malformed, REGISTRY, {"ro.evaluate-boron": handler}, verified, now=NOW)
    assert calls == []


def test_dispatch_rejects_stale_mismatched_and_ungated_confirmation_without_execution():
    calls = []
    handler = lambda arguments, envelope: calls.append(True)
    with pytest.raises(ContractValidationError, match="stale"):
        dispatch_tool(request(), REGISTRY, {"ro.evaluate-boron": handler}, verified,
                      now=datetime(2026, 9, 1, 0, 6, tzinfo=timezone.utc))
    mismatched = request()
    mismatched["confirmation"]["action_id"] = "action-other"
    with pytest.raises(ContractValidationError, match="exact request/action"):
        dispatch_tool(mismatched, REGISTRY, {"ro.evaluate-boron": handler}, verified, now=NOW)
    with pytest.raises(ContractValidationError, match="could not be verified"):
        dispatch_tool(request(), REGISTRY, {"ro.evaluate-boron": handler}, lambda confirmation, binding: False, now=NOW)
    with pytest.raises(ContractValidationError, match="could not be verified"):
        dispatch_tool(request(), REGISTRY, {"ro.evaluate-boron": handler}, now=NOW)
    assert calls == []


def test_confirmation_is_bound_to_arguments_and_context():
    changed_arguments = deepcopy(request())
    changed_arguments["arguments"] = {"report": False}
    with pytest.raises(ContractValidationError, match="exact request/action"):
        dispatch_tool(changed_arguments, REGISTRY, {}, verified, now=NOW)
    changed_context = deepcopy(request())
    changed_context["context"]["context_id"] = "context-2"
    with pytest.raises(ContractValidationError, match="exact request/action"):
        dispatch_tool(changed_context, REGISTRY, {}, verified, now=NOW)
