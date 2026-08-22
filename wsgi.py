"""Production WSGI entry point for Total Water Design Suite v0.25.

The suite hosts the authenticated account/launcher shell and the Total RO Design
v0.2 engineering application in one Flask deployment. Existing TOTALRO_*
environment names are retained for in-place AWS compatibility.
"""
import os

os.environ.setdefault("TOTALRO_DEPLOYMENT_MODE", "server")
os.environ.setdefault("TOTALRO_AUTH_ENABLED", "1")
os.environ.setdefault("TOTALRO_COMPUTE_MODE", "cpu")
os.environ.setdefault("TOTALRO_MAX_ENGINEERING_WORKERS", "auto")

# Install the advanced chemistry layer before Flask imports calculations.py.
# This preserves the existing public API while ensuring every hosted Alpha
# calculation uses the upgraded pH/speciation/neutral-ammonia chemistry.
from runtime_chemistry_upgrade import install_runtime_chemistry  # noqa: E402

CHEMISTRY_UPGRADE = install_runtime_chemistry()

from app import app  # noqa: E402
