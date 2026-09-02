import os

os.environ.setdefault("TOTALRO_AUTH_ENABLED", "0")
os.environ.setdefault("TOTALRO_CSRF_ENABLED", "0")

from app import app
from auth import MobileDeviceSession, MobilePushToken, User, db, login_manager


def _client_and_user():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    login_manager.session_protection = None
    with app.app_context():
        db.drop_all(); db.create_all()
        user = User(email="mobile@example.test", full_name="Mobile User", password_hash="x", status="active")
        db.session.add(user); db.session.commit()
        user_id, version = user.id, user.password_version
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = f"{user_id}:{version}"; session["_fresh"] = True
    return client


def _register(client, device="ios-1"):
    response = client.post("/v1/auth/device-sessions", json={"device_id": device, "platform": "ios", "device_name": "Phone"}, headers={"Accept-Contract": "twds.mobile.auth/v1"})
    assert response.status_code == 201
    return response.get_json()


def _headers(envelope):
    return {"Accept-Contract": "twds.mobile.auth/v1", "Authorization": f"Bearer {envelope['access_token']}"}


def test_mobile_refresh_is_single_use_and_reuse_compromises_session():
    client = _client_and_user(); envelope = _register(client)
    refreshed = client.post("/v1/auth/refresh", json={"device_id": "ios-1", "refresh_token": envelope["refresh_token"]}, headers={"Accept-Contract": "twds.mobile.auth/v1"})
    assert refreshed.status_code == 200
    reused = client.post("/v1/auth/refresh", json={"device_id": "ios-1", "refresh_token": envelope["refresh_token"]}, headers={"Accept-Contract": "twds.mobile.auth/v1"})
    assert reused.status_code == 401
    assert reused.get_json()["code"] == "TOKEN_REUSED"
    with app.app_context():
        assert db.session.get(MobileDeviceSession, envelope["session_id"]).state == "compromised"


def test_device_logout_and_push_lifecycle_are_scoped_to_current_session():
    client = _client_and_user(); envelope = _register(client)
    headers = _headers(envelope)
    assert client.post("/v1/mobile/push-tokens", json={"provider": "apns", "token": "push-token"}, headers=headers).status_code == 204
    assert client.post("/v1/mobile/push-tokens", json={"provider": "apns", "token": "push-token-rotated"}, headers=headers).status_code == 204
    assert client.delete("/v1/mobile/push-tokens", json={"token": "push-token-rotated"}, headers=headers).status_code == 204
    assert client.post("/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/v1/auth/device-sessions", headers=headers).get_json()["code"] == "UNAUTHENTICATED"
    with app.app_context():
        assert db.session.query(MobilePushToken).count() == 0


def test_navigation_and_notification_payloads_reject_urls_unknown_routes_and_wrong_versions():
    client = _client_and_user(); headers = _headers(_register(client))
    assert client.post("/v1/mobile/navigation", json={"contract": "twds.mobile.auth/v1", "route": "https://evil.example"}, headers=headers).status_code == 400
    assert client.post("/v1/mobile/navigation", json={"contract": "twds.mobile.auth/v1", "route": "report", "url": "https://evil.example"}, headers=headers).status_code == 400
    assert client.post("/v1/mobile/navigation", json={"contract": "twds.mobile.auth/v1", "route": "report", "resource_id": "r-1"}, headers=headers).get_json()["route"] == "report"
    bad = {"version": 2, "navigationInput": {"contract": "twds.mobile.auth/v1", "route": "report"}}
    assert client.post("/v1/mobile/notification-payloads/validate", json=bad, headers=headers).status_code == 400
    good = {"version": 1, "navigationInput": {"contract": "twds.mobile.auth/v1", "route": "device_sessions"}}
    assert client.post("/v1/mobile/notification-payloads/validate", json=good, headers=headers).get_json()["valid"] is True


def test_contract_major_is_negotiated_at_runtime():
    client = _client_and_user()
    response = client.post("/v1/auth/device-sessions", json={"device_id": "ios-1", "platform": "ios"}, headers={"Accept-Contract": "twds.mobile.auth/v2"})
    assert response.status_code == 406
    assert response.get_json()["code"] == "VERSION_UNSUPPORTED"
