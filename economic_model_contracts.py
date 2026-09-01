"""Versioned contracts for the Total Water Economics model store."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


CONTRACT_VERSIONS = {
    "twds.economic_model": "1.0",
    "twds.economic_summary": "1.0",
    "twds.cost_item": "1.0",
    "twds.capex_wbs": "1.0",
    "twds.inflation_profile": "1.0",
    "twds.cpi_snapshot": "1.0",
    "twds.insurance_policy": "1.0",
    "twds.land_right": "1.0",
    "twds.financing_tranche": "1.0",
    "twds.financial_scenario": "1.0",
}


class ContractError(ValueError):
    """A persisted object has an unknown or invalid contract version."""


Migration = Callable[[dict[str, Any]], dict[str, Any]]
_MIGRATIONS: dict[tuple[str, str, str], Migration] = {}


def contract_header(contract_id: str) -> dict[str, str]:
    try:
        version = CONTRACT_VERSIONS[contract_id]
    except KeyError as exc:
        raise ContractError(f"Unknown TWDS contract: {contract_id}") from exc
    return {"contract_id": contract_id, "contract_version": version}


def register_migration(contract_id: str, source: str, target: str, migration: Migration) -> None:
    if contract_id not in CONTRACT_VERSIONS:
        raise ContractError(f"Unknown TWDS contract: {contract_id}")
    _MIGRATIONS[(contract_id, source, target)] = migration


def validate_contract(document: dict[str, Any], expected_id: str | None = None) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ContractError("Contract document must be an object.")
    contract_id = str(document.get("contract_id") or "")
    version = str(document.get("contract_version") or "")
    if expected_id and contract_id != expected_id:
        raise ContractError(f"Expected {expected_id}, received {contract_id or '(missing)' }.")
    if contract_id not in CONTRACT_VERSIONS:
        raise ContractError(f"Unknown TWDS contract: {contract_id or '(missing)'}")
    current = CONTRACT_VERSIONS[contract_id]
    if version != current:
        raise ContractError(
            f"Unsupported {contract_id} version {version or '(missing)'}; migrate to {current}."
        )
    return deepcopy(document)


def migrate_contract(document: dict[str, Any], target_version: str | None = None) -> dict[str, Any]:
    result = deepcopy(document)
    contract_id = str(result.get("contract_id") or "")
    if contract_id not in CONTRACT_VERSIONS:
        raise ContractError(f"Unknown TWDS contract: {contract_id or '(missing)'}")
    target = target_version or CONTRACT_VERSIONS[contract_id]
    seen: set[str] = set()
    while str(result.get("contract_version") or "") != target:
        source = str(result.get("contract_version") or "")
        if source in seen:
            raise ContractError(f"Migration cycle for {contract_id} at {source}.")
        seen.add(source)
        candidates = [key for key in _MIGRATIONS if key[0] == contract_id and key[1] == source]
        if len(candidates) != 1:
            raise ContractError(f"No unambiguous migration for {contract_id} {source} to {target}.")
        key = candidates[0]
        result = _MIGRATIONS[key](deepcopy(result))
        result["contract_id"], result["contract_version"] = contract_id, key[2]
    return validate_contract(result, contract_id) if target == CONTRACT_VERSIONS[contract_id] else result
