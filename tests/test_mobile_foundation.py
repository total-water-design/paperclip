import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileFoundationTests(unittest.TestCase):
    def test_manifest_is_valid_and_hosted(self):
        manifest_path = ROOT / "static" / "manifest.webmanifest"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "Total Water Design Suite")
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["display"], "standalone")
        icon_sizes = {icon.get("sizes") for icon in manifest.get("icons", [])}
        self.assertIn("192x192", icon_sizes)
        self.assertIn("512x512", icon_sizes)
        self.assertTrue((ROOT / "static" / "branding" / "suite" / "total_water_design_suite_icon_192.svg").exists())
        self.assertTrue((ROOT / "static" / "branding" / "suite" / "total_water_design_suite_icon_512.png").exists())

    def test_primary_surfaces_load_mobile_layer(self):
        templates = [
            ROOT / "templates" / "suite_landing.html",
            ROOT / "templates" / "suite_dashboard.html",
            ROOT / "templates" / "auth" / "base.html",
            ROOT / "templates" / "index.html",
        ]
        for template in templates:
            with self.subTest(template=template.name):
                text = template.read_text(encoding="utf-8")
                self.assertIn("manifest.webmanifest", text)
                self.assertIn("mobile.css", text)
                self.assertIn("mobile.js", text)
                self.assertIn("viewport-fit=cover", text)

    def test_service_worker_never_handles_engineering_api_or_navigation(self):
        worker = (ROOT / "static" / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn("request.method !== 'GET'", worker)
        self.assertIn("url.pathname.startsWith('/static/')", worker)
        self.assertNotIn("/api/", "\n".join(
            line for line in worker.splitlines()
            if "CORE_ASSETS" in line or line.lstrip().startswith("'/")
        ))
        self.assertIn("fetch(request)", worker)
        self.assertIn("caches.match(request)", worker)
        self.assertIn("total_water_design_suite_icon_192.svg", worker)

    def test_mobile_layer_has_no_solver_or_project_api_calls(self):
        mobile_js = (ROOT / "static" / "mobile.js").read_text(encoding="utf-8")
        self.assertNotIn("/api/calculate", mobile_js)
        self.assertNotIn("/api/chemistry", mobile_js)
        self.assertNotIn("/api/projects", mobile_js)
        self.assertIn("mobile-sidebar-open", mobile_js)
        self.assertIn("serviceWorker.register('/static/service-worker.js')", mobile_js)

    def test_mobile_css_defines_phone_and_tablet_breakpoints(self):
        css = (ROOT / "static" / "mobile.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width:1024px)", css)
        self.assertIn("@media (max-width:900px)", css)
        self.assertIn("@media (max-width:600px)", css)
        self.assertIn("env(safe-area-inset-top", css)
        self.assertIn("min-height:var(--twds-mobile-touch)", css)
        self.assertIn("min(calc(100vw - 20px),760px)", css)


if __name__ == "__main__":
    unittest.main()
