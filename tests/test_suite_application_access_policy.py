from types import SimpleNamespace

import auth
from suite_catalog import PRODUCT_BY_ID


class Entitlement:
    def __init__(self, *, enabled=True, current=True):
        self.enabled = enabled
        self._current = current

    def is_current(self):
        return self._current


def user(*, admin=False, status="active"):
    return SimpleNamespace(id=41, is_admin=admin, status=status)


def test_admin_access_matches_catalog_preview_readiness(monkeypatch):
    monkeypatch.setattr(auth, "product_entitlement_for", lambda *_: None)
    account = user(admin=True)
    for product_id in ("bio", "zld", "academy"):
        assert PRODUCT_BY_ID[product_id].admin_preview_enabled
        assert auth.user_can_access_product(account, product_id)
    for product_id in ("pretreatment", "post_treatment", "balance", "economics", "system_integration"):
        assert not PRODUCT_BY_ID[product_id].admin_preview_enabled
        assert not auth.user_can_access_product(account, product_id)


def test_active_entitlement_accesses_only_available_or_preview_ready_apps(monkeypatch):
    monkeypatch.setattr(auth, "product_entitlement_for", lambda *_: Entitlement())
    account = user()
    for product_id in ("ro", "bio", "zld", "academy"):
        assert auth.user_can_access_product(account, product_id)
    for product_id in ("pretreatment", "post_treatment", "balance", "economics", "system_integration"):
        assert not auth.user_can_access_product(account, product_id)


def test_disabled_expired_and_inactive_accounts_are_denied(monkeypatch):
    account = user()
    monkeypatch.setattr(auth, "product_entitlement_for", lambda *_: Entitlement(enabled=False))
    assert not auth.user_can_access_product(account, "bio")
    monkeypatch.setattr(auth, "product_entitlement_for", lambda *_: Entitlement(current=False))
    assert not auth.user_can_access_product(account, "zld")
    monkeypatch.setattr(auth, "product_entitlement_for", lambda *_: Entitlement())
    assert not auth.user_can_access_product(user(status="pending"), "academy")
