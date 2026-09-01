import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).parents[1] / "contracts" / "assistant" / "v1"


def load(name):
    return json.loads((ROOT / name).read_text())


def test_contract_schemas_are_valid_draft_2020_12():
    for name in (
        "assistant-manifest.schema.json",
        "assistant-response.schema.json",
        "semantic-target-registry.schema.json",
        "tool-registration.schema.json",
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
