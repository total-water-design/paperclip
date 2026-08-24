"""Shared aqueous-chemistry contract for Total Water Design Suite."""

from .engine import (
    equilibrate,
    prepare_handoff,
    recalculate_after_process_change,
    receive_handoff,
)
from .water_state import SCHEMA_ID, SCHEMA_VERSION, WaterState
from .waterstream_adapter import (
    ADAPTER_VERSION,
    CHEMISTRY_REFERENCE_SHA,
    WATERSTREAM_REFERENCE_SHA,
    WATERSTREAM_SCHEMA_ID,
    WATERSTREAM_SCHEMA_VERSION,
    SharedChemistryCertificateIssuer,
    WaterStreamAdapterError,
    certify_waterstream,
    equilibrate_waterstream,
    waterstream_to_waterstate,
)

__all__ = [
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "WaterState",
    "equilibrate",
    "prepare_handoff",
    "recalculate_after_process_change",
    "receive_handoff",
    "ADAPTER_VERSION",
    "CHEMISTRY_REFERENCE_SHA",
    "WATERSTREAM_REFERENCE_SHA",
    "WATERSTREAM_SCHEMA_ID",
    "WATERSTREAM_SCHEMA_VERSION",
    "SharedChemistryCertificateIssuer",
    "WaterStreamAdapterError",
    "certify_waterstream",
    "equilibrate_waterstream",
    "waterstream_to_waterstate",
]
