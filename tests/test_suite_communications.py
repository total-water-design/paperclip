from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_whats_new_uses_release_records_not_branches():
    service = read("suite_communications.py")
    landing = read("templates/suite_landing.html")
    assert 'ReleaseRecord' in service
    assert 'RoadmapItem' in service
    assert 'commercial_launch_window' in service
    assert "{% set whats_new = twds_whats_new|default" in landing
    assert "whats_new.recently_updated" in landing
    assert "whats_new.roadmap" in landing
    assert "whats_new.commercial_launch_window" in landing
    assert 'git branch' not in landing.lower()


def test_release_must_be_validated_deployed_and_healthy():
    text = read("suite_communications.py")
    assert 'self.validated_at' in text
    assert 'self.deployed_at' in text
    assert 'self.health_verified_at' in text
    assert 'release.is_customer_ready()' in text
    assert 'update_email_approved' in text


def test_product_update_email_is_opt_in_and_plain_language():
    text = read("suite_communications.py")
    template = read("templates/auth/communication_preferences.html")
    assert 'product_updates_enabled' in text
    assert 'product_updates_enabled.is_(True)' in text
    assert "What's new in" in text
    assert 'Thank you for using Total Water Design Suite' in text
    assert 'git commit' not in text.lower()
    assert 'product_updates_enabled' in template


def test_admin_controls_commercial_launch_and_roadmap():
    template = read("templates/auth/admin_communications.html")
    assert 'Commercial launch' in template
    assert 'Customer-facing summary' in template
    assert 'Deployment health verified' in template
    assert 'Approved for product-update email' in template
