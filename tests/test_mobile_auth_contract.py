import json
from pathlib import Path

import jsonschema
import pytest


SCHEMA_PATH = Path(__file__).parents[1] / "contracts" / "mobile" / "auth" / "v1" / "auth-device-session.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())


def valid_session():
    return {
        "contract": "twds.mobile.auth/v1", "session_id": "session-1", "device_id": "device-1",
        "owner": {"tenant_id": "tenant-1", "user_id": "user-1"},
        "created_at": "2026-09-02T00:00:00Z", "last_seen_at": "2026-09-02T00:01:00Z",
        "state": "active", "refresh_generation": 3,
    }


def test_schema_is_valid_and_accepts_each_shared_shape():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    samples = [
        valid_session(),
        {"contract": "twds.mobile.auth/v1", "transaction_id": "mfa-1", "purpose": "authentication", "state": "pending", "expires_at": "2026-09-02T00:05:00Z", "allowed_methods": ["totp"]},
        {"contract": "twds.mobile.auth/v1", "request_id": "privacy-1", "owner": {"tenant_id": "tenant-1", "user_id": "user-1"}, "kind": "export", "state": "queued", "requested_at": "2026-09-02T00:00:00Z"},
        {"contract": "twds.mobile.auth/v1", "route": "device_sessions", "reauthentication_required": True},
        {"contract": "twds.mobile.auth/v1", "code": "OFFLINE", "retryable": False, "request_id": "request-1"},
    ]
    for sample in samples:
        VALIDATOR.validate(sample)


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(contract="twds.mobile.auth/v2"),
    lambda value: value.update(refresh_generation=-1),
    lambda value: value.update(owner={"tenant_id": "tenant-1", "user_id": "user-1", "role": "admin"}),
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


def test_error_taxonomy_rejects_ad_hoc_codes_and_secret_details():
    VALIDATOR.validate({"contract": "twds.mobile.auth/v1", "code": "TOKEN_REUSED", "retryable": False, "request_id": "request-1"})
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate({"contract": "twds.mobile.auth/v1", "code": "PASSWORD_WRONG_FOR_ALICE", "retryable": False, "request_id": "request-1"})
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate({"contract": "twds.mobile.auth/v1", "code": "MFA_INVALID", "retryable": False, "request_id": "request-1", "proof": "123456"})
