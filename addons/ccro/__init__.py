"""Total RO Design Closed Circuit RO add-on registration."""
from __future__ import annotations

from .engine import ccro

ADDON_ID = "totalrodesign.ccro"
ADDON_VERSION = "1.1.0"
FEATURE_ID = "ccro"


def register_ccro(app, calculations, require_feature=None):
    """Register CCRO without modifying the host calculation/entitlement files."""
    if getattr(app, "_totalro_ccro_registered", False):
        return

    # CALCS is a mutable host registry imported from calculations.py. Extending
    # it here keeps the host calculations.py byte-identical.
    calculations["ccro"] = ccro

    # Flask is imported only when the host registers the add-on. Keeping Flask
    # out of module import time lets source/engineering tests run independently.
    from flask import jsonify

    @app.get("/api/addons/ccro/status")
    def _ccro_status():
        return jsonify({
            "ok": True,
            "addon": ADDON_ID,
            "version": ADDON_VERSION,
            "mode": "ccro",
            "minimum_tier": "entry",
            "available_all_tiers": True,
        })

    app._totalro_ccro_registered = True
