"""End-to-end API integration tests using FastAPI TestClient."""
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client(monkeypatch):
    tmp = Path(tempfile.mkdtemp()) / "api_test.db"
    monkeypatch.setattr("app.utils.token_store.DB_PATH", tmp)
    from app.main import create_app
    app = create_app()
    return TestClient(app)


# ---- Root ----

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "AzureRedOps"


def test_cors_allows_localhost_frontends(client):
    origin = "http://localhost:5174"
    r = client.get("/", headers={"Origin": origin})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == origin


# ---- Activities ----

def test_run_activity(client):
    r = client.post("/activities/run", json={
        "activity": "list-users",
        "token_name": "mytoken",
        "flags": {"beta": True, "json": "users.json"},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["activity"] == "list-users"
    assert "list-users" in data["stdout"]


def test_run_activity_minimal(client):
    r = client.post("/activities/run", json={"activity": "self"})
    assert r.status_code == 200


# ---- Tokens ----

def test_save_list_get_decode_delete_token(client):
    save = client.post("/tokens/save", json={
        "name": "demo",
        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.sig",
        "refresh_token": "rt",
        "account": "[email protected]",
        "scope": "Mail.Read",
        "client_id": "abcd",
        "expires_in": 3600,
    })
    assert save.status_code == 200
    assert save.json()["ok"] is True

    listed = client.get("/tokens/")
    assert listed.status_code == 200
    assert any(t["name"] == "demo" for t in listed.json())

    raw = client.get("/tokens/demo/raw")
    assert raw.status_code == 200
    assert raw.json()["account"] == "[email protected]"

    access = client.get("/tokens/demo/access")
    assert access.status_code == 200
    assert access.json()["access_token"].startswith("eyJ")

    decoded = client.get("/tokens/demo/decode")
    assert decoded.status_code == 200
    d = decoded.json()
    assert d["payload"]["sub"] == "test"
    assert d["signature_present"] is True

    delete = client.delete("/tokens/demo")
    assert delete.status_code == 200
    assert client.get("/tokens/demo/raw").status_code == 404


def test_decode_raw_token(client):
    payload = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ4IiwibmFtZSI6IlllcyJ9.X"
    r = client.post("/tokens/decode-raw", json={"token": payload})
    assert r.status_code == 200
    data = r.json()
    assert data["payload"]["sub"] == "x"
    assert data["payload"]["name"] == "Yes"


def test_get_token_404(client):
    r = client.get("/tokens/nope/raw")
    assert r.status_code == 404


def test_refresh_missing_token(client):
    save = client.post("/tokens/save", json={
        "name": "no_rt", "access_token": "at",
    })
    assert save.status_code == 200
    r = client.post("/tokens/no_rt/refresh")
    assert r.status_code == 400


# ---- OAuth Device Flow ----

def test_full_device_flow(client):
    start = client.post("/oauth/device/start", json={
        "session_email": "[email protected]",
    })
    assert start.status_code == 200
    flow = start.json()
    assert flow["user_code"]
    assert flow["device_code"]
    assert "microsoft.com/devicelogin" in flow["verification_url"]

    listed = client.get("/oauth/device")
    assert listed.status_code == 200
    assert any(d["user_code"] == flow["user_code"] for d in listed.json())

    get = client.get(f"/oauth/device/{flow['device_code']}")
    assert get.status_code == 200
    assert get.json()["status"] == "pending"

    submit = client.post("/oauth/device/submit", json={
        "device_code": flow["device_code"],
        "access_token": "captured_at_123",
        "refresh_token": "captured_rt_456",
        "account": "[email protected]",
        "scope": "Mail.Read",
        "client_id": "client_x",
    })
    assert submit.status_code == 200
    name = submit.json()["token_name"]
    assert name.startswith("phish-")

    # token is now retrievable
    raw = client.get(f"/tokens/{name}/raw")
    assert raw.status_code == 200
    assert raw.json()["access_token"] == "captured_at_123"
    assert raw.json()["account"] == "[email protected]"

    # flow marked captured
    after = client.get(f"/oauth/device/{flow['device_code']}")
    assert after.json()["status"] == "captured"


def test_device_flow_404_on_unknown(client):
    r = client.get("/oauth/device/does-not-exist")
    assert r.status_code == 404


# ---- Sessions ----

def test_sessions_list(client):
    r = client.get("/sessions/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_session_cookies(client):
    r = client.get("/sessions/1/cookies")
    assert r.status_code == 200
    assert "cookies" in r.json()


def test_session_mail_token(client):
    r = client.get("/sessions/1/mail-token")
    assert r.status_code == 200
    assert "token" in r.json()


# ---- Spraying ----

def test_spray(client):
    r = client.post("/spray/", params={
        "username": "[email protected]",
        "password": "P@ssw0rd!",
        "tenant_id": "tenant-guid",
        "check_privs": True,
    })
    assert r.status_code == 200
    assert r.json()["username"] == "[email protected]"
    assert r.json()["check_privs"] is True


# ---- Phishing ----

def test_generate_lure(client):
    r = client.post("/phish/lure/generate", json={
        "template": "OneDrive",
        "secret_path": "share/doc-123",
    })
    assert r.status_code == 200
    assert "share/doc-123" in r.json()["url"]


# ---- Auth ----

def test_ropc(client):
    r = client.post("/auth/ropc", params={
        "username": "[email protected]",
        "password": "secret",
        "token_name": "t",
    })
    assert r.status_code == 200
    assert r.json()["username"] == "[email protected]"


def test_device_auth(client):
    r = client.post("/auth/device/start", params={"tid": "tid"})
    assert r.status_code == 200
    r = client.post("/auth/device/capture", params={"user_code": "ABC123"})
    assert r.status_code == 200


# ---- Mailbox ----

def test_mailbox_sessions_crud(client):
    add = client.post("/mailbox/sessions", json={
        "name": "mb1", "email": "[email protected]",
        "imap_host": "outlook.office365.com",
        "imap_port": 993, "password": "pw", "use_ssl": True,
    })
    assert add.status_code == 200
    lst = client.get("/mailbox/sessions")
    assert lst.status_code == 200
    assert any(s["name"] == "mb1" for s in lst.json())
    delete = client.delete("/mailbox/sessions/mb1")
    assert delete.status_code == 200
    assert not any(s["name"] == "mb1" for s in client.get("/mailbox/sessions").json())


def test_mailbox_proxy_404_on_missing(client):
    r = client.get("/mailbox/proxy/no-exist/folders")
    assert r.status_code == 404
    r = client.get("/mailbox/proxy/no-exist/messages")
    assert r.status_code == 404


def test_mailbox_forward(client):
    client.post("/mailbox/sessions", json={
        "name": "mb2", "email": "[email protected]",
        "imap_host": "imap.example.com", "password": "pw",
    })
    r = client.post(
        "/mailbox/proxy/mb2/forward",
        json={"to": "[email protected]", "msg_id": "1", "folder": "INBOX"},
    )
    assert r.status_code == 200


# ---- OpenAPI doc loads ----

def test_openapi_docs(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for p in ["/", "/activities/run", "/tokens/", "/oauth/device/start",
              "/oauth/device/{device_code}", "/mailbox/sessions",
              "/spray/", "/phish/lure/generate", "/sessions/"]:
        assert p in paths, f"missing path {p}"
