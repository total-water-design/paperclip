#!/usr/bin/env python3
"""Fail-closed, non-mutating evidence validator for TWDS host candidates."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

RUNNER = "/home/paperclip/.venvs/tot57/bin/python"
BROWSER = "/home/paperclip/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome"
GH = "/usr/local/bin/gh-validation"


def run(argv: list[str], cwd: Path, out: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    name = f"{len(list(out.glob('*.stdout'))):02d}-{Path(argv[0]).name}"
    (out / f"{name}.command").write_text(" ".join(argv) + "\n")
    (out / f"{name}.stdout").write_text(result.stdout)
    (out / f"{name}.stderr").write_text(result.stderr)
    return result


def git(cwd: Path, out: Path, *args: str) -> str:
    result = run(["git", *args], cwd, out)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} exited {result.returncode}")
    return result.stdout.strip()


def api_request(base_url: str, key: str, method: str, path: str, payload: dict[str, object], out: Path) -> object:
    """Capture both control-plane request and response as validator evidence."""
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}", data=body, method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    name = f"{len(list(out.glob('*.stdout'))):02d}-paperclip-api"
    (out / f"{name}.command").write_text(f"{method} {path}\n")
    (out / f"{name}.stdout").write_text(body.decode() + "\n")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = response.read().decode()
            (out / f"{name}.stderr").write_text("")
            (out / f"{name}.response").write_text(result)
            return json.loads(result)
    except urllib.error.HTTPError as exc:
        result = exc.read().decode()
        (out / f"{name}.stderr").write_text(f"HTTP {exc.code}\n{result}")
        raise RuntimeError(f"Paperclip writeback returned HTTP {exc.code}") from exc


def api_get(base_url: str, key: str, path: str, out: Path) -> object:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}", headers={"Authorization": f"Bearer {key}"},
    )
    name = f"{len(list(out.glob('*.stdout'))):02d}-paperclip-verify"
    (out / f"{name}.command").write_text(f"GET {path}\n")
    (out / f"{name}.stdout").write_text("")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = response.read().decode()
            (out / f"{name}.stderr").write_text("")
            (out / f"{name}.response").write_text(result)
            return json.loads(result)
    except urllib.error.HTTPError as exc:
        result = exc.read().decode()
        (out / f"{name}.stderr").write_text(f"HTTP {exc.code}\n{result}")
        raise RuntimeError(f"Paperclip verification returned HTTP {exc.code}") from exc


def finalize(report: dict[str, object], args: argparse.Namespace, artifacts: Path) -> None:
    """Write and verify the technical verdict; a human gate is a separate interaction."""
    if not (args.originating_issue_id and args.paperclip_api_url and args.paperclip_api_key):
        raise RuntimeError("originating issue and Paperclip credentials are required for finalization")
    verdict = str(report["verdict"])
    next_step = str(report["nextStep"])
    body = f"Host validation verdict: {verdict}\n\nCandidate: {report['requestedSha']}\nNext step: {next_step}"
    api_request(args.paperclip_api_url, args.paperclip_api_key, "POST", f"/api/issues/{args.originating_issue_id}/comments", {"body": body}, artifacts)
    api_request(args.paperclip_api_url, args.paperclip_api_key, "PATCH", f"/api/issues/{args.originating_issue_id}", {"status": args.final_status}, artifacts)
    verified = api_get(args.paperclip_api_url, args.paperclip_api_key, f"/api/issues/{args.originating_issue_id}", artifacts)
    if not isinstance(verified, dict) or verified.get("status") != args.final_status:
        raise RuntimeError("Paperclip status writeback was not persisted")
    comments = api_get(args.paperclip_api_url, args.paperclip_api_key, f"/api/issues/{args.originating_issue_id}/comments", artifacts)
    comment_items = comments.get("comments", comments) if isinstance(comments, dict) else comments
    if not isinstance(comment_items, list) or not any(isinstance(item, dict) and item.get("body") == body for item in comment_items):
        raise RuntimeError("Paperclip verdict comment writeback was not persisted")
    if args.human_review_required:
        interaction = api_request(args.paperclip_api_url, args.paperclip_api_key, "POST", f"/api/issues/{args.originating_issue_id}/interactions", {
            "kind": "request_confirmation", "resolverPolicy": "human_only",
            "title": "Human review required", "prompt": "Review the host-validation evidence and approve or reject the decision gate.",
        }, artifacts)
        if not isinstance(interaction, dict) or interaction.get("status") != "pending" or interaction.get("resolverPolicy") != "human_only":
            raise RuntimeError("fresh human-only interaction was not persisted as pending")
        interactions = api_get(args.paperclip_api_url, args.paperclip_api_key, f"/api/issues/{args.originating_issue_id}/interactions", artifacts)
        interaction_items = interactions.get("interactions", interactions) if isinstance(interactions, dict) else interactions
        if not isinstance(interaction_items, list) or not any(isinstance(item, dict) and item.get("id") == interaction.get("id") for item in interaction_items):
            raise RuntimeError("human-only interaction writeback was not retrievable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--requested-sha", required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--localhost-url", required=True)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--gh-validation", default=GH)
    parser.add_argument("--originating-issue-id", required=True)
    parser.add_argument("--paperclip-api-url", required=True)
    parser.add_argument("--paperclip-api-key", required=True)
    parser.add_argument("--final-status", choices=["in_progress", "in_review", "blocked", "done"], required=True)
    parser.add_argument("--human-review-required", action="store_true")
    args = parser.parse_args()

    checkout = args.checkout.resolve()
    requested = args.requested_sha.lower()
    artifacts = args.artifact_root.resolve() / requested
    artifacts.mkdir(parents=True, exist_ok=True)
    checks: dict[str, object] = {
        "runner": {"path": RUNNER, "executable": os.access(RUNNER, os.X_OK)},
        "browser": {"path": BROWSER, "executable": os.access(BROWSER, os.X_OK)},
        "ambientGithubTokensRemoved": True,
    }
    report: dict[str, object] = {"version": 1, "verdict": "NOT ESTABLISHED", "checkout": str(checkout), "requestedSha": requested, "origin": args.origin, "artifacts": str(artifacts), "checks": checks}
    try:
        if len(requested) != 40 or any(c not in "0123456789abcdef" for c in requested):
            raise RuntimeError("requested SHA must be 40 lowercase hexadecimal characters")
        if not RUNNER or not os.access(RUNNER, os.X_OK):
            raise RuntimeError(f"runner is not executable: {RUNNER}")
        if not os.access(BROWSER, os.X_OK):
            raise RuntimeError(f"browser is not executable: {BROWSER}")
        if git(checkout, artifacts, "status", "--porcelain"):
            raise RuntimeError("checkout is dirty")
        if run(["git", "symbolic-ref", "-q", "HEAD"], checkout, artifacts).returncode == 0:
            raise RuntimeError("checkout must be detached at the exact candidate SHA")
        resolved = git(checkout, artifacts, "rev-parse", "HEAD")
        if resolved != requested or git(checkout, artifacts, "rev-parse", f"{requested}^{{commit}}") != requested:
            raise RuntimeError("requested and resolved SHA differ")
        checks["resolvedSha"] = resolved
        if git(checkout, artifacts, "remote", "get-url", "origin") != args.origin:
            raise RuntimeError("authoritative origin mismatch")
        remote_ref = git(checkout, artifacts, "ls-remote", args.origin, f"refs/heads/{args.target_branch}").split()
        if not remote_ref or remote_ref[0] != requested:
            raise RuntimeError("target-fork branch does not resolve to the requested SHA")
        checks["targetForkSha"] = remote_ref[0]
        if run([RUNNER, "-c", "import playwright; print(playwright.__file__)"], checkout, artifacts).returncode:
            raise RuntimeError("Playwright does not import under the required runner")
        checks["playwrightImport"] = "PASS"
        browser_code = ("from playwright.sync_api import sync_playwright; "
                        f"p=sync_playwright().start(); b=p.chromium.launch(executable_path={BROWSER!r}); "
                        f"page=b.new_page(); r=page.goto({args.localhost_url!r}, wait_until='domcontentloaded'); "
                        "print(r.status if r else 'no-response'); b.close(); p.stop()")
        if run([RUNNER, "-c", browser_code], checkout, artifacts).returncode:
            raise RuntimeError("localhost browser execution failed")
        checks["localhostBrowserExecution"] = "PASS"
        gh_env = {k: v for k, v in os.environ.items() if k not in {"GH_TOKEN", "GITHUB_TOKEN"}}
        gh = run([args.gh_validation, "auth", "status"], checkout, artifacts, gh_env)
        if gh.returncode or "totalrodesign-tech" not in (gh.stdout + gh.stderr):
            raise RuntimeError("gh-validation did not establish reviewer identity totalrodesign-tech")
        checks["ghReviewerIdentity"] = "totalrodesign-tech"
        report["verdict"] = "PASS"
        report["nextStep"] = "Proceed with the originating TOT's next execution stage."
    except Exception as exc:  # evidence/provisioning failures must never become candidate FAIL
        report["error"] = str(exc)
        report["nextStep"] = "Repair host provisioning or evidence capture; candidate technical result is NOT ESTABLISHED."
    try:
        finalize(report, args, artifacts)
        report["finalization"] = "verified"
    except Exception as exc:
        # Control-plane proof is required evidence, so it fails closed too.
        report["verdict"] = "NOT ESTABLISHED"
        report["error"] = str(exc)
        report["nextStep"] = "Repair finalization writeback or evidence capture; candidate technical result is NOT ESTABLISHED."
    (artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
