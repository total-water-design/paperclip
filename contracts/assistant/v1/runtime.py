"""Deterministic validation and dispatch for the shared assistant contracts.

This module is deliberately outside solver modules.  It validates immutable
solver snapshots and invokes only an explicitly registered Python callable.
"""

from __future__ import annotations

import json
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import jsonschema


ROOT = Path(__file__).parent


class ContractValidationError(ValueError):
    """A published contract or semantic registry constraint was violated."""


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _validate(instance: Mapping[str, Any], schema_name: str) -> None:
    schema = _load(schema_name)
    local_schemas = {
        item["$id"]: item
        for item in (_load("context-envelope.schema.json"), schema)
        if "$id" in item
    }
    resolver = jsonschema.RefResolver((ROOT / schema_name).as_uri(), schema, store=local_schemas)
    try:
        jsonschema.Draft202012Validator(schema, resolver=resolver).validate(dict(instance))
    except jsonschema.ValidationError as exc:
        raise ContractValidationError(exc.message) from exc


def validate_context_envelope(envelope: Mapping[str, Any]) -> None:
    """Validate a serialization boundary, including failure-state propagation."""
    _validate(envelope, "context-envelope.schema.json")
    convergence = envelope["convergence"]
    if convergence["state"] in {"non_converged", "failed"} and "failure" not in convergence:
        raise ContractValidationError("non-converged and failed contexts require convergence.failure")


def build_context_envelope(
    *, context_id: str, source: Mapping[str, Any], water_state: Mapping[str, Any], streams: Iterable[Any],
    composition: Mapping[str, float], speciation: Mapping[str, Any], mass_energy_balance: Mapping[str, Any],
    convergence: Mapping[str, Any], units: Mapping[str, str], handoff: Mapping[str, Any],
) -> dict[str, Any]:
    """Serialize existing application-owned solver state at the shared boundary.

    A WaterStream-like object may expose ``to_dict``; otherwise a mapping is
    accepted. The function intentionally does not calculate chemistry, balances,
    or convergence values.
    """
    serialized_streams = [stream.to_dict() if hasattr(stream, "to_dict") else dict(stream) for stream in streams]
    envelope = {
        "contract": "twds.assistant.context/v1", "context_id": context_id, "source": dict(source),
        "waterstream": {"water_state": dict(water_state), "streams": serialized_streams},
        "chemistry": {"composition": dict(composition), "speciation": dict(speciation)},
        "mass_energy_balance": dict(mass_energy_balance), "convergence": dict(convergence),
        "units": dict(units), "handoff": dict(handoff),
    }
    validate_context_envelope(envelope)
    return envelope


def validate_action(action: Mapping[str, Any], targets: Mapping[str, Any], tools: Mapping[str, Any]) -> None:
    """Resolve a proposed action against the manifest's semantic registries."""
    kind = action.get("kind")
    if kind in {"navigate", "highlight"}:
        target_ids = {item["target_id"] for item in targets.get("targets", [])}
        if action.get("target_id") not in target_ids:
            raise ContractValidationError("action target_id is not registered")
    elif kind == "propose_tool":
        tool_ids = {item["tool_id"] for item in tools.get("tools", [])}
        if action.get("tool_id") not in tool_ids:
            raise ContractValidationError("action tool_id is not registered")
        if action.get("requires_confirmation") is not True:
            raise ContractValidationError("tool actions require confirmation")
    else:
        raise ContractValidationError("action kind is not supported")


def confirmation_request_digest(request: Mapping[str, Any], action_id: str) -> str:
    """Return the canonical digest a confirmation must authorize."""
    binding = {
        "action_id": action_id, "request_id": request.get("request_id"),
        "tool_id": request.get("tool_id"), "arguments": request.get("arguments"),
        "context": request.get("context"),
    }
    encoded = json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_confirmation(request, verifier, now) -> None:
    confirmation = request["confirmation"]
    try:
        issued_at = datetime.fromisoformat(confirmation["issued_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(confirmation["expires_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ContractValidationError("confirmation timestamps are malformed") from exc
    checked_at = now or datetime.now(timezone.utc)
    if issued_at.tzinfo is None or expires_at.tzinfo is None or checked_at.tzinfo is None:
        raise ContractValidationError("confirmation timestamps must include a timezone")
    if expires_at <= issued_at or checked_at < issued_at or checked_at >= expires_at:
        raise ContractValidationError("confirmation is stale or outside its validity period")
    expected = confirmation_request_digest(request, confirmation["action_id"])
    if not hmac.compare_digest(confirmation["request_digest"], expected):
        raise ContractValidationError("confirmation does not match the exact request/action")
    binding = {"action_id": confirmation["action_id"], "request_id": request["request_id"],
               "tool_id": request["tool_id"], "request_digest": expected}
    try:
        verified = verifier is not None and verifier(confirmation, binding) is True
    except Exception as exc:
        raise ContractValidationError("confirmation verifier rejected malformed evidence") from exc
    if not verified:
        raise ContractValidationError("confirmation could not be verified")


def dispatch_tool(
    request: Mapping[str, Any], registry: Mapping[str, Any], handlers: Mapping[str, Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]],
    confirmation_verifier: Callable[[Mapping[str, Any], Mapping[str, Any]], bool] | None = None,
    *, now: datetime | None = None,
) -> dict[str, Any]:
    """Validate and call one registered deterministic tool, returning its contract result.

    Handlers receive ``arguments`` and the validated context envelope.  They do
    not receive an assistant prompt or model object, so solver paths remain
    deterministic and model-free.
    """
    _validate(request, "tool-request.schema.json")
    validate_context_envelope(request["context"])
    _validate_confirmation(request, confirmation_verifier, now)
    tool = next((entry for entry in registry.get("tools", []) if entry.get("tool_id") == request["tool_id"]), None)
    if tool is None or tool.get("deterministic") is not True:
        raise ContractValidationError("request tool_id is not a registered deterministic tool")
    try:
        jsonschema.Draft202012Validator(tool["input_schema"]).validate(request["arguments"])
    except jsonschema.ValidationError as exc:
        raise ContractValidationError("tool arguments: " + exc.message) from exc
    handler = handlers.get(request["tool_id"])
    if handler is None:
        raise ContractValidationError("no deterministic handler is registered for tool_id")
    payload = dict(handler(request["arguments"], request["context"]))
    try:
        jsonschema.Draft202012Validator(tool["output_schema"]).validate(payload.get("output", {}))
    except jsonschema.ValidationError as exc:
        raise ContractValidationError("tool output: " + exc.message) from exc
    result = {
        "contract": "twds.assistant.tool-result/v1", "request_id": request["request_id"],
        "tool_id": request["tool_id"], "status": payload.get("status", "succeeded"),
        "output": payload.get("output", {}), "provenance": payload.get("provenance", {}),
    }
    if "failure" in payload:
        result["failure"] = payload["failure"]
    if result["provenance"].get("context_id") != request["context"]["context_id"]:
        raise ContractValidationError("result provenance must identify the request context")
    _validate(result, "tool-result.schema.json")
    return result
