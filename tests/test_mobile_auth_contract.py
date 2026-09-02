import json
from pathlib import Path

import jsonschema
import pytest
from referencing import Registry, Resource


SCHEMA_PATH = Path(__file__).parents[1] / "contracts" / "mobile" / "auth" / "v1" / "auth-device-session.schema.json"
COMMON_PATH = Path(__file__).parents[1] / "contracts" / "mobile" / "v1" / "common.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())
COMMON = json.loads(COMMON_PATH.read_text())
REGISTRY = Registry().with_resource(COMMON["$id"], Resource.from_contents(COMMON))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA, registry=REGISTRY, format_checker=jsonschema.FormatChecker())


def valid_session():
    return {
        "contract": "twds.mobile.auth/v1", "session_id": "session-1", "device_id": "device-1",
        "principal": {"tenant_id": "tenant-1", "user_id": "user-1"},
        "created_at": "2026-09-02T00:00:00Z", "last_seen_at": "2026-09-02T00:01:00Z",
        "state": "active", "refresh_generation": 3,
    }


def test_schema_is_valid_and_accepts_each_shared_shape():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    samples = [
        valid_session(),
        {"contract": "twds.mobile.auth/v1", "transaction_id": "mfa-1", "purpose": "authentication", "state": "pending", "expires_at": "2026-09-02T00:05:00Z", "allowed_methods": ["totp"]},
        {"contract": "twds.mobile.auth/v1", "request_id": "privacy-1", "principal": {"tenant_id": "tenant-1", "user_id": "user-1"}, "kind": "export", "state": "queued", "requested_at": "2026-09-02T00:00:00Z"},
        {"contract": "twds.mobile.auth/v1", "route": "device_sessions", "reauthentication_required": True},
        {"contract": "twds.mobile.auth/v1", "code": "OFFLINE", "message": "Connectivity is unavailable.", "retryable": False, "request_id": "request-1"},
    ]
    for sample in samples:
        VALIDATOR.validate(sample)


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(contract="twds.mobile.auth/v2"),
    lambda value: value.update(refresh_generation=-1),
    lambda value: value.update(principal={"tenant_id": "tenant-1", "user_id": "user-1", "role": "admin"}),
    lambda value: value.update(access_token="secret"),
])
def test_session_rejects_unknown_major_invalid_generation_privilege_and_tokens(mutation):
    value = valid_session()
    mutation(value)
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate(value)


@pytest.mark.parametrize("route", ["https://evil.example", "javascript:alert(1)", "admin", "/privacy"])
def test_navigation_rejects_non_allowlisted_targets(route):
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate({"contract": "twds.mobile.auth/v1", "route": route})


@pytest.mark.parametrize("value", [
    {"contract": "twds.mobile.auth/v1", "route": "project", "project_id": "project-1"},
    {"contract": "twds.mobile.auth/v1", "route": "job", "resource_id": "job-1"},
    {"contract": "twds.mobile.auth/v1", "route": "report", "resource_id": "report-1"},
])
def test_resource_navigation_accepts_exactly_one_canonical_identifier(value):
    VALIDATOR.validate(value)


@pytest.mark.parametrize("value", [
    {"contract": "twds.mobile.auth/v1", "route": "project", "resource_id": "project-1"},
    {"contract": "twds.mobile.auth/v1", "route": "job", "resource_id": "job-1", "project_id": "project-1"},
    {"contract": "twds.mobile.auth/v1", "route": "report", "resource_id": "report-1", "revision_id": "revision-1"},
    {"contract": "twds.mobile.auth/v1", "route": "privacy", "resource_id": "privacy-1"},
])
def test_navigation_rejects_missing_or_irrelevant_identifiers(value):
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate(value)


def test_error_taxonomy_rejects_ad_hoc_codes_and_secret_details():
    VALIDATOR.validate({"contract": "twds.mobile.auth/v1", "code": "TOKEN_REUSED", "message": "This session can no longer be used.", "retryable": False, "request_id": "request-1", "retry_after_seconds": 2})
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate({"contract": "twds.mobile.auth/v1", "code": "PASSWORD_WRONG_FOR_ALICE", "message": "Sign-in failed.", "retryable": False, "request_id": "request-1"})
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate({"contract": "twds.mobile.auth/v1", "code": "MFA_INVALID", "message": "MFA proof is invalid.", "retryable": False, "request_id": "request-1", "proof": "123456"})
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate({"contract": "twds.mobile.auth/v1", "code": "MFA_INVALID", "message": "refresh_token: secret", "retryable": False, "request_id": "request-1"})
