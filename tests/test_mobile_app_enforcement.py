import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileAppEnforcementSourceTests(unittest.TestCase):
    def test_mobile_policy_module_is_present_and_disabled_by_default(self):
        source = (ROOT / "mobile_access.py").read_text(encoding="utf-8")
        self.assertIn('TOTALRO_REQUIRE_MOBILE_APP_ON_PHONE", False', source)
        self.assertIn('REQUIRE_MOBILE_APP_ON_PHONE', source)
        self.assertIn('raise RuntimeError(', source)
        self.assertIn('attestation verifiers are configured', source)

    def test_phone_detection_uses_server_visible_hints(self):
        source = (ROOT / "mobile_access.py").read_text(encoding="utf-8")
        self.assertIn('Sec-CH-UA-Mobile', source)
        self.assertIn('iphone|ipod', source.lower())
        self.assertIn('android[^;)]*mobile', source.lower())
        self.assertNotIn('X-TWDS-Device-Class', source)

    def test_native_app_session_is_server_signed_and_account_bound(self):
        source = (ROOT / "mobile_access.py").read_text(encoding="utf-8")
        self.assertIn('URLSafeTimedSerializer', source)
        self.assertIn('MOBILE_APP_COOKIE', source)
        self.assertIn('int(claims.get("uid", -1)) != int(current_user.id)', source)
        self.assertIn('httponly=True', source)
        self.assertIn('secure=bool(current_app.config.get("SESSION_COOKIE_SECURE", False))', source)

    def test_app_verification_is_attestation_pluggable_not_header_trust(self):
        source = (ROOT / "mobile_access.py").read_text(encoding="utf-8")
        self.assertIn('twds_mobile_attestation_verifiers', source)
        self.assertIn('attestation_verifier_not_configured', source)
        self.assertIn('attestation_rejected', source)
        self.assertNotIn('X-TWDS-App-Verified', source)
        self.assertNotIn('X-TWDS-App-Platform', source)

    def test_phone_browser_engineering_routes_are_blocked_with_upgrade_required(self):
        source = (ROOT / "mobile_access.py").read_text(encoding="utf-8")
        self.assertIn('"/suite", "/ro"', source)
        self.assertIn('"/api/"', source)
        self.assertIn('return jsonify({', source)
        self.assertIn('MobileAppRequired', source)
        self.assertIn('}), 426', source)
        self.assertIn('mobile_app_required.html', source)

    def test_public_and_mobile_bootstrap_routes_are_not_engineering_gate_targets(self):
        source = (ROOT / "mobile_access.py").read_text(encoding="utf-8")
        self.assertIn('if path.startswith(_MOBILE_API_PREFIX):', source)
        self.assertIn('if path == "/api/suite/catalog":', source)
        self.assertNotIn('_PROTECTED_EXACT = {"/",', source)
        self.assertNotIn('"/login"', source.split('_PROTECTED_PREFIXES', 1)[0])

    def test_customer_block_screen_and_store_configuration_exist(self):
        template = (ROOT / "templates" / "mobile_app_required.html").read_text(encoding="utf-8")
        env_example = (ROOT / "deploy" / "totalrodesign.env.example").read_text(encoding="utf-8")
        self.assertIn('Continue in the mobile app', template)
        self.assertIn('Download for iPhone', template)
        self.assertIn('Download for Android', template)
        self.assertIn('TOTALRO_REQUIRE_MOBILE_APP_ON_PHONE=0', env_example)
        self.assertIn('TOTALRO_IOS_APP_STORE_URL=', env_example)
        self.assertIn('TOTALRO_ANDROID_PLAY_STORE_URL=', env_example)

    def test_wsgi_registers_policy_without_changing_engineering_modules(self):
        wsgi = (ROOT / "wsgi.py").read_text(encoding="utf-8")
        self.assertIn('from mobile_access import init_mobile_access', wsgi)
        self.assertIn('init_mobile_access(app)', wsgi)
        source = (ROOT / "mobile_access.py").read_text(encoding="utf-8")
        self.assertNotIn('from calculations import', source)
        self.assertNotIn('from chemistry_analysis import', source)
        self.assertNotIn('from compute_engine import', source)


if __name__ == "__main__":
    unittest.main()
