from datetime import datetime, timezone
import unittest

from app import app
from auth import AccountAudit, LoginAddress, ProductEntitlement, User, db


class EconomicsApiAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        with app.app_context():
            db.create_all()

    def setUp(self):
        self.original_config = {
            key: app.config.get(key)
            for key in ("AUTH_ENABLED", "DEPLOYMENT_MODE", "WTF_CSRF_ENABLED")
        }
        app.config.update(WTF_CSRF_ENABLED=False)
        self.client = app.test_client()

    def tearDown(self):
        with app.app_context():
            user_ids = [row[0] for row in db.session.query(User.id).filter(
                User.email.like("tot420-%@example.test")
            )]
            if user_ids:
                db.session.query(AccountAudit).filter(
                    (AccountAudit.user_id.in_(user_ids)) | (AccountAudit.actor_user_id.in_(user_ids))
                ).delete(synchronize_session=False)
                db.session.query(LoginAddress).filter(LoginAddress.user_id.in_(user_ids)).delete(
                    synchronize_session=False
                )
                db.session.query(ProductEntitlement).filter(ProductEntitlement.user_id.in_(user_ids)).delete(
                    synchronize_session=False
                )
                db.session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
            db.session.commit()
            db.session.remove()
        app.config.update(self.original_config)

    @staticmethod
    def economics_payload():
        return {
            "model": "total_economic_design",
            "project": {"project_name": "Authorization Test", "currency": "USD", "capacity_m3d": 10000},
            "source_summaries": [],
            "cost_items": [{
                "item_id": "equipment-1", "description": "Equipment", "bucket": "equipment_purchase",
                "quantity": 1, "unit": "LS", "unit_cost": 10_000_000, "currency": "USD",
                "source_type": "user", "source_reference": "TOT-420 authorization test",
            }],
            "allowances": {},
            "operating": {
                "capacity_m3d": 10000, "availability": 0.95, "fixed_opex_y": 1_000_000,
                "other_opex_y": 0, "project_life_years": 25, "discount_rate": 0.06,
            },
        }

    def test_governed_runtime_rejects_ungated_requests_even_with_preview_header(self):
        app.config.update(AUTH_ENABLED=False, DEPLOYMENT_MODE="server")

        no_header = self.client.post("/api/economics", json=self.economics_payload())
        forged_header = self.client.post(
            "/api/economics",
            headers={"X-TotalRO-Effective-Tier": "platinum"},
            json=self.economics_payload(),
        )

        for response in (no_header, forged_header):
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.get_json()["error_type"], "EconomicsAuthorizationError")
        self.assertEqual(no_header.get_json(), forged_header.get_json())

    def test_authenticated_economics_entitlement_accepts_finance_request(self):
        app.config.update(AUTH_ENABLED=True, DEPLOYMENT_MODE="server")
        with app.app_context():
            user = User(
                email="tot420-economics@example.test",
                full_name="TOT-420 Test User",
                organization="TWDS",
                role="user",
                licensed_tier="entry",
                status="active",
                terms_accepted_at=datetime.now(timezone.utc),
            )
            user.set_password("TOT-420 test password")
            db.session.add(user)
            db.session.flush()
            db.session.add(ProductEntitlement(
                user_id=user.id,
                product_id="economics",
                enabled=True,
                tier="gold",
                status="active",
            ))
            db.session.commit()
        login = self.client.post("/login", data={
            "email": "tot420-economics@example.test",
            "password": "TOT-420 test password",
        })
        self.assertEqual(login.status_code, 302)

        response = self.client.post("/api/economics", json=self.economics_payload())

        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertIn("cost_hierarchy", result)
        self.assertIn("operating", result)


if __name__ == "__main__":
    unittest.main()
