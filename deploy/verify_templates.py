#!/usr/bin/env python3
"""Compile every Jinja template before an AWS package is accepted.

This catches unclosed blocks and other template syntax errors without needing a
running database, browser session, or production Flask configuration.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_ROOT)),
    autoescape=select_autoescape(("html", "xml")),
)

failures: list[str] = []
# Packaging regression gate: a previous build accidentally converted the Jinja
# token "% e" inside "{% endblock %}" into scientific notation and left a
# visible literal such as "{ 0.000000e+00ndblock" in several auth pages.
# Jinja compilation alone cannot detect that because the junk is valid text.
MALFORMED_TEMPLATE_ARTIFACT = re.compile(
    r"\{\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+ndblock\b",
    re.IGNORECASE,
)
templates = sorted(
    path.relative_to(TEMPLATE_ROOT).as_posix()
    for path in TEMPLATE_ROOT.rglob("*")
    if path.is_file() and path.suffix.lower() in {".html", ".jinja", ".j2"}
)

for name in templates:
    path = TEMPLATE_ROOT / name
    try:
        source = path.read_text(encoding="utf-8")
    except Exception as exc:
        failures.append(f"{name}: unable to read template: {type(exc).__name__}: {exc}")
        continue

    artifact = MALFORMED_TEMPLATE_ARTIFACT.search(source)
    if artifact:
        failures.append(
            f"{name}: malformed template artifact found: {artifact.group(0)!r}"
        )
        continue

    try:
        env.get_template(name)
    except TemplateSyntaxError as exc:
        failures.append(f"{name}:{exc.lineno}: {exc.message}")
    except Exception as exc:  # pragma: no cover - defensive packaging gate
        failures.append(f"{name}: {type(exc).__name__}: {exc}")

if failures:
    print("Jinja template compilation: FAILED", file=sys.stderr)
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)
    raise SystemExit(1)

print(f"Jinja template compilation: PASSED ({len(templates)} templates)")
