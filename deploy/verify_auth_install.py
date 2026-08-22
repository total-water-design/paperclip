#!/usr/bin/env python3
"""Isolated authenticated-suite smoke test used by the Ubuntu installer.

The installer runs this against a temporary SQLite database before copying the
release into the live application directory. It validates the shared suite
login, additive product entitlements, direct RO entry, and tier enforcement.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import tempfile

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

with tempfile.TemporaryDirectory(prefix="totalwater-suite-auth-check-") as tmp:
    db_path = Path(tmp) / "auth-check.db"
    os.environ.update(
        {
            "TOTALRO_DEPLOYMENT_MODE": "server",
            "TOTALRO_AUTH_ENABLED": "1",
            "TOTALRO_CSRF_ENABLED": "0",
            "TOTALRO_SECRET_KEY": "installer-check-" + "x" * 64,
            "TOTALRO_DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
            "TOTALRO_AUTO_CREATE_DB": "1",
            "TOTALRO_COOKIE_SECURE": "0",
            "TOTALRO_TRUSTED_HOSTS": "localhost,127.0.0.1",
            "TOTALRO_SMTP_HOST": "",
            "CALCOSPOWER_TEST_SERIAL": "1",
            "TOTALRO_COMPUTE_MODE": "cpu",
            "TOTALRO_MAX_ENGINEERING_WORKERS": "auto",
            "CALCOSPOWER_DISABLE_GPU": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )

    import app as app_module  # noqa: E402
    from auth import (  # noqa: E402
        LoginAddress,
        ProductEntitlement,
        ProjectRevision,
        User,
        db,
        ensure_default_entitlements,
    )

    app = app_module.app
    app.config.update(TESTING=True)
    accepted = datetime.now(timezone.utc)
    with app.app_context():
        db.create_all()
        admin = User(
            email="admin-check@totalrodesign.com",
            full_name="Installer Admin",
            organization="Total Water Design Suite",
            role="admin",
            licensed_tier="platinum",
            status="active",
            terms_accepted_at=accepted,
            password_hash="",
        )
        admin.set_password("Installer-Check-Password-Admin")
        user = User(
            email="entry-check@example.com",
            full_name="Installer Entry",
            organization="Example Engineering",
            role="user",
            licensed_tier="entry",
            status="active",
            terms_accepted_at=accepted,
            password_hash="",
        )
        user.set_password("Installer-Check-Password-Entry")
        db.session.add_all([admin, user])
        db.session.flush()
        admin_products = ensure_default_entitlements(admin, flush=True)
        entry_products = ensure_default_entitlements(user, flush=True)
        admin_products["ro"].enabled = True
        admin_products["ro"].tier = "platinum"
        entry_products["ro"].enabled = True
        entry_products["ro"].tier = "entry"
        db.session.commit()
        admin_id = admin.id
        assert admin.password_hash.startswith("scrypt:")
        assert db.session.query(ProductEntitlement).count() >= 14

    client = app.test_client()

    # Public suite endpoints.
    health = client.get("/healthz")
    assert health.status_code == 200
    health_json = health.get_json()
    assert health_json["application"] == "Total Water Design Suite"
    assert health_json["suite_version"] == "0.25"
    assert health_json["component"] == "Total RO Design"
    assert client.get("/").status_code == 200
    catalog = client.get("/api/suite/catalog")
    assert catalog.status_code == 200
    catalog_json = catalog.get_json()
    assert catalog_json["suite"]["version"] == "0.25"
    assert any(p["product_id"] == "ro" and p["status"] == "available" for p in catalog_json["products"])

    # Protected suite/application endpoints redirect before login.
    assert client.get("/suite").status_code == 302
    assert client.get("/ro").status_code == 302
    assert client.get("/api/entitlements").status_code == 401

    # Entry account: one login, suite dashboard, direct RO access, no spoofed tier.
    login = client.post(
        "/login",
        data={"email": "entry-check@example.com", "password": "Installer-Check-Password-Entry"},
    )
    assert login.status_code == 302
    assert "/suite" in login.headers["Location"]
    assert client.get("/suite").status_code == 200
    assert client.get("/ro").status_code == 200
    entry = client.get(
        "/api/entitlements",
        headers={"X-TotalRO-Effective-Tier": "platinum"},
    ).get_json()
    assert entry["effective_tier"] == "entry"
    assert entry["features"]["erd"]["allowed"] is False
    ro_product = next(p for p in entry["products"] if p["product_id"] == "ro")
    assert ro_product["accessible"] is True
    assert ro_product["entitlement"]["tier"] == "entry"
    assert client.post("/logout").status_code == 302

    # Revocation is enforced server-side on the application and API.
    with app.app_context():
        db_user = db.session.query(User).filter_by(email="entry-check@example.com").one()
        ro_row = db.session.query(ProductEntitlement).filter_by(user_id=db_user.id, product_id="ro").one()
        ro_row.enabled = False
        db.session.commit()
    client.post(
        "/login",
        data={"email": "entry-check@example.com", "password": "Installer-Check-Password-Entry"},
    )
    assert client.get("/ro").status_code == 302
    denied = client.get("/api/entitlements")
    assert denied.status_code == 403
    client.post("/logout")

    # Administrator retains all four preview tiers without changing the licensed tier.
    admin_login = client.post(
        "/login",
        data={"email": "admin-check@totalrodesign.com", "password": "Installer-Check-Password-Admin"},
    )
    assert admin_login.status_code == 302
    assert client.get("/suite").status_code == 200
    platinum = client.get(
        "/api/entitlements",
        headers={"X-TotalRO-Effective-Tier": "platinum"},
    ).get_json()
    assert platinum["is_admin"] is True
    assert platinum["licensed_tier"] == "platinum"
    assert platinum["effective_tier"] == "platinum"
    admin_users_page = client.get("/admin/users")
    assert admin_users_page.status_code == 200
    assert b"userSearch" in admin_users_page.data
    admin_projects_page = client.get("/admin/projects")
    assert admin_projects_page.status_code == 200
    assert b"projectSearch" in admin_projects_page.data

    # Administrator-created accounts support product-specific entitlements.
    created_user = client.post(
        "/admin/users/create",
        data={
            "full_name": "Product Entitlement Check",
            "email": "product-check@example.com",
            "organization": "Example Engineering",
            "role": "user",
            "new_product_ro_enabled": "1",
            "new_product_ro_tier": "silver",
            "new_product_bio_enabled": "1",
            "new_product_bio_tier": "platinum",
        },
    )
    assert created_user.status_code == 302
    with app.app_context():
        product_user = db.session.query(User).filter_by(email="product-check@example.com").one()
        rows = {row.product_id: row for row in db.session.query(ProductEntitlement).filter_by(user_id=product_user.id)}
        assert product_user.licensed_tier == "silver"
        assert rows["ro"].enabled is True and rows["ro"].tier == "silver"
        assert rows["bio"].enabled is True and rows["bio"].tier == "platinum"
        assert rows["zld"].enabled is False

    # Successful login IP history is persisted for administrator review.
    with app.app_context():
        assert db.session.query(LoginAddress).filter_by(user_id=admin_id).count() >= 1

    # Authenticated project saves create a private Suite project family and TROD revision ID.
    snapshot = {
        "format": "Total RO Design Project",
        "schema_version": 7,
        "app_version": "0.2",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "project": {"project_name": "Installer Project", "revision": "Rev 0"},
        "active_case": 1,
        "active_mode": "water",
        "units": {"flow": "m3/h", "pressure": "bar", "flux": "LMH"},
        "cases": {"1": {"waterProfile": {"temperature_c": 25.0}}},
    }
    created = client.post("/api/projects", json={"snapshot": snapshot})
    assert created.status_code == 201, created.get_data(as_text=True)
    project = created.get_json()["project"]
    assert project["visible_id"].startswith("TROD-")
    assert project["revision"] == 0
    listed = client.get("/api/projects")
    assert listed.status_code == 200
    assert any(row["visible_id"] == project["visible_id"] for row in listed.get_json()["projects"])
    copied = client.post(f"/api/projects/{project['id']}/copy", json={})
    assert copied.status_code == 201
    assert copied.get_json()["project"]["revision"] == 1
    assert client.get("/admin/projects").status_code == 200
    inspected = client.get(f"/admin/projects/{project['id']}/json")
    assert inspected.status_code == 200
    with app.app_context():
        assert db.session.query(ProjectRevision).count() == 2
        from auth import AccountAudit
        assert db.session.query(AccountAudit).filter_by(action="admin_project_inspected").count() == 1

print("Total Water Design Suite v0.25 Alpha authenticated-server smoke test: PASSED")
