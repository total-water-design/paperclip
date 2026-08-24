"""Local QR rendering for Suite MFA enrollment.

The provisioning payload never leaves the process. This module deliberately has
no HTTP, telemetry, logging, or analytics integration.
"""
from __future__ import annotations

import base64
import io

import segno


def qr_svg_data_uri(payload: str) -> str:
    """Return a high-contrast SVG QR data URI for a TOTP provisioning payload."""

    value = str(payload or "")
    if not value.startswith("otpauth://totp/"):
        raise ValueError("A standard TOTP provisioning URI is required.")
    qr = segno.make(value, error="M", micro=False)
    buffer = io.BytesIO()
    qr.save(
        buffer,
        kind="svg",
        scale=6,
        border=4,
        dark="#000000",
        light="#ffffff",
        xmldecl=False,
        svgns=True,
    )
    return "data:image/svg+xml;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
