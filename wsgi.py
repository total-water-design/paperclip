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

from app import app  # noqa: E402
