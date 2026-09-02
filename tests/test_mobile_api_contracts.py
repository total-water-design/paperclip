import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).parents[1] / "contracts" / "mobile" / "v1"
NAMES = ("common", "session", "job", "report", "event", "deep-link", "error")


def load(name):
    return json.loads((ROOT / f"{name}.schema.json").read_text())


def validator(name):
    schemas = [load(item) for item in NAMES]
    root = load(name)
    resolver = jsonschema.RefResolver.from_schema(root, store={schema["$id"]: schema for schema in schemas})
    return jsonschema.Draft202012Validator(root, resolver=resolver)


def principal():
    return {"tenant_id": "tenant-1", "user_id": "user-1", "scopes": ["jobs:read", "jobs:write"]}


def provenance():
    return {"candidate_sha": "a" * 40, "engine": "total-ro", "submitted_at": "2026-09-02T00:00:00Z", "input_digest": "sha256:" + "b" * 64}


def test_all_schemas_are_valid_and_refs_resolve():
    for name in NAMES:
        jsonschema.Draft202012Validator.check_schema(load(name))
        validator(name)


def test_job_requires_owner_continuity_idempotency_and_server_provenance():
    job = {"contract": "twds.mobile/v1", "job_id": "job-1", "operation": "calculate", "status": "queued", "owner": principal(), "continuity": {"project_id": "p-1", "revision_id": "r-2", "parent_revision_id": "r-1"}, "provenance": provenance(), "idempotency_key": "0123456789abcdef", "created_at": "2026-09-02T00:00:00Z"}
    validator("job").validate(job)
    for field in ("owner", "continuity", "provenance", "idempotency_key"):
        broken = dict(job); broken.pop(field)
        with pytest.raises(jsonschema.ValidationError): validator("job").validate(broken)


def test_terminal_jobs_require_result_or_structured_error():
    base = {"contract": "twds.mobile/v1", "job_id": "job-1", "operation": "generate_report", "owner": principal(), "continuity": {"project_id": "p-1", "revision_id": "r-1"}, "provenance": provenance(), "idempotency_key": "0123456789abcdef", "created_at": "2026-09-02T00:00:00Z"}
    with pytest.raises(jsonschema.ValidationError): validator("job").validate({**base, "status": "succeeded"})
    with pytest.raises(jsonschema.ValidationError): validator("job").validate({**base, "status": "failed"})
    validator("job").validate({**base, "status": "succeeded", "result": {"report_id": "report-1"}})


def test_deep_links_reject_arbitrary_urls_and_unknown_major():
    validator("deep-link").validate({"contract": "twds.mobile/v1", "route": "report", "resource_id": "report-1", "project_id": "p-1"})
    with pytest.raises(jsonschema.ValidationError): validator("deep-link").validate({"contract": "twds.mobile/v1", "route": "https://evil.example", "resource_id": "report-1"})
    with pytest.raises(jsonschema.ValidationError): validator("deep-link").validate({"contract": "twds.mobile/v2", "route": "report", "resource_id": "report-1"})


def test_report_downloads_are_https_and_events_have_monotonic_domain_sequence():
    report = {"contract": "twds.mobile/v1", "report_id": "report-1", "job_id": "job-1", "owner": principal(), "continuity": {"project_id": "p-1", "revision_id": "r-1"}, "provenance": provenance(), "media_type": "application/pdf", "download_url": "https://download.example/report-1", "expires_at": "2026-09-02T00:05:00Z"}
    validator("report").validate(report)
    report["download_url"] = "javascript:alert(1)"
    with pytest.raises(jsonschema.ValidationError): validator("report").validate(report)
    event = {"contract": "twds.mobile/v1", "event_id": "event-1", "sequence": 1, "kind": "job.updated", "occurred_at": "2026-09-02T00:00:00Z", "owner": principal(), "resource": {"type": "job", "id": "job-1"}, "cursor": "opaque-next"}
    validator("event").validate(event)
    event["sequence"] = 0
    with pytest.raises(jsonschema.ValidationError): validator("event").validate(event)
