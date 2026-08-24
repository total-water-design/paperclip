#!/usr/bin/env python3
"""Deterministically fingerprint a pip requirements include graph.

Deployment-infrastructure helper. It recursively follows local ``-r`` and
``--requirement`` includes, fails closed on unsafe graphs, and hashes each
manifest path, exact bytes, and include edges. A transitive manifest change
therefore changes the closure fingerprint even when the top-level requirements
file is byte-identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
from dataclasses import dataclass
from pathlib import Path


class RequirementsFingerprintError(RuntimeError):
    """Raised when a requirements include graph is unsafe or invalid."""


@dataclass(frozen=True)
class ManifestRecord:
    path: str
    sha256: str
    includes: tuple[str, ...]


def _strip_comment(line: str) -> str:
    if not line.strip() or line.lstrip().startswith("#"):
        return ""
    out: list[str] = []
    quoted: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            out.append(char)
            escaped = False
            continue
        if char == "\\":
            out.append(char)
            escaped = True
            continue
        if quoted:
            out.append(char)
            if char == quoted:
                quoted = None
            continue
        if char in {"'", '"'}:
            quoted = char
            out.append(char)
            continue
        if char == "#" and (index == 0 or line[index - 1].isspace()):
            break
        out.append(char)
    return "".join(out).strip()


def _include_targets(text: str) -> list[str]:
    targets: list[str] = []
    logical = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.endswith("\\"):
            logical += line[:-1] + " "
            continue
        logical += line
        clean = _strip_comment(logical)
        logical = ""
        if not clean:
            continue
        try:
            tokens = shlex.split(clean, posix=True)
        except ValueError as exc:
            raise RequirementsFingerprintError(f"Invalid requirements line: {clean!r}: {exc}") from exc
        i = 0
        while i < len(tokens):
            token = tokens[i]
            target: str | None = None
            if token in {"-r", "--requirement"}:
                if i + 1 >= len(tokens):
                    raise RequirementsFingerprintError(f"Missing include target in line: {clean!r}")
                target = tokens[i + 1]
                i += 2
            elif token.startswith("--requirement="):
                target = token.split("=", 1)[1]
                i += 1
            elif token.startswith("-r") and token != "-r":
                target = token[2:]
                i += 1
            else:
                i += 1
            if target is not None:
                if target.startswith(("http://", "https://", "git+", "file://")):
                    raise RequirementsFingerprintError(
                        f"Remote requirement includes are not permitted for deployment fingerprinting: {target}"
                    )
                if not target.strip():
                    raise RequirementsFingerprintError(f"Empty include target in line: {clean!r}")
                targets.append(target)
    if logical.strip():
        raise RequirementsFingerprintError("Requirements file ends with an unterminated line continuation")
    return targets


def build_manifest_graph(root_manifest: Path, repo_root: Path | None = None) -> list[ManifestRecord]:
    repo_root = (repo_root or root_manifest.parent).resolve()
    root_manifest = root_manifest.resolve()
    try:
        root_manifest.relative_to(repo_root)
    except ValueError as exc:
        raise RequirementsFingerprintError("Root manifest must be inside the repository root") from exc

    records: dict[Path, ManifestRecord] = {}
    visiting: list[Path] = []

    def visit(path: Path) -> None:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(repo_root)
        except ValueError as exc:
            raise RequirementsFingerprintError(f"Requirement include escapes repository root: {path}") from exc
        if resolved in visiting:
            cycle = " -> ".join(str(p.relative_to(repo_root)) for p in [*visiting, resolved])
            raise RequirementsFingerprintError(f"Requirement include cycle detected: {cycle}")
        if resolved in records:
            return
        if not resolved.is_file():
            raise RequirementsFingerprintError(f"Requirement manifest does not exist: {relative.as_posix()}")

        data = resolved.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RequirementsFingerprintError(f"Requirement manifest is not UTF-8: {relative.as_posix()}") from exc

        visiting.append(resolved)
        includes: list[str] = []
        for target in _include_targets(text):
            included = (resolved.parent / target).resolve()
            try:
                included_rel = included.relative_to(repo_root).as_posix()
            except ValueError as exc:
                raise RequirementsFingerprintError(
                    f"Requirement include escapes repository root: {relative.as_posix()} -> {target}"
                ) from exc
            includes.append(included_rel)
            visit(included)
        visiting.pop()

        records[resolved] = ManifestRecord(
            path=relative.as_posix(),
            sha256=hashlib.sha256(data).hexdigest(),
            includes=tuple(includes),
        )

    visit(root_manifest)
    return sorted(records.values(), key=lambda row: row.path)


def fingerprint(root_manifest: Path, repo_root: Path | None = None) -> tuple[str, list[ManifestRecord]]:
    records = build_manifest_graph(root_manifest, repo_root)
    canonical = json.dumps(
        [
            {"path": row.path, "sha256": row.sha256, "includes": list(row.includes)}
            for row in records
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest(), records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default="requirements-server.txt")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    digest, records = fingerprint(Path(args.manifest), Path(args.repo_root))
    if args.as_json:
        print(json.dumps({
            "fingerprint": digest,
            "manifests": [
                {"path": row.path, "sha256": row.sha256, "includes": list(row.includes)}
                for row in records
            ],
        }, sort_keys=True))
    else:
        print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
