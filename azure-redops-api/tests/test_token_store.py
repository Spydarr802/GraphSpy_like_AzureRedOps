"""Tests for the persistent token store (uses tmp DB)."""
import os
import tempfile
from pathlib import Path


def setup_test_db(monkeypatch):
    tmp = Path(tempfile.mkdtemp()) / "test_tokens.db"
    monkeypatch.setattr("app.utils.token_store.DB_PATH", tmp)
    from app.utils import token_store
    token_store.init()
    return token_store, tmp


def test_save_and_get_token(monkeypatch):
    ts, _ = setup_test_db(monkeypatch)
    ts.save_token("test1", {
        "access_token": "at_abc",
        "refresh_token": "rt_xyz",
        "scope": "Mail.Read",
        "account": "[email protected]",
        "expires_in": 3600,
        "expires_on": 9999999999,
        "client_id": "d3590ed6-52b3-4102-aeff-aad2292ab01c",
    })
    assert ts.get_token("test1")["access_token"] == "at_abc"
    assert ts.get_token("test1")["account"] == "[email protected]"
    assert "test1" in [t["name"] for t in ts.list_tokens()]


def test_update_token_on_conflict(monkeypatch):
    ts, _ = setup_test_db(monkeypatch)
    ts.save_token("t", {"access_token": "old"})
    ts.save_token("t", {"access_token": "new"})
    assert ts.get_token("t")["access_token"] == "new"
    assert len(ts.list_tokens()) == 1


def test_delete_token(monkeypatch):
    ts, _ = setup_test_db(monkeypatch)
    ts.save_token("delme", {"access_token": "x"})
    ts.delete_token("delme")
    assert ts.get_token("delme") is None


def test_mailbox_session_crud(monkeypatch):
    ts, _ = setup_test_db(monkeypatch)
    ts.save_mailbox_session("mb1", "[email protected]", "outlook.office365.com", 993, "p@ss")
    s = ts.get_mailbox_session("mb1")
    assert s is not None
    assert s["email"] == "[email protected]"
    assert s["imap_host"] == "outlook.office365.com"
    assert 1 == len(ts.list_mailbox_sessions())
    ts.delete_mailbox_session("mb1")
    assert ts.get_mailbox_session("mb1") is None


def test_device_flow_lifecycle(monkeypatch):
    ts, _ = setup_test_db(monkeypatch)
    flow = ts.start_device_capture("[email protected]")
    assert flow["user_code"]
    assert flow["device_code"]
    assert flow["verification_url"].startswith("https://")
    fetched = ts.get_device_flow(flow["device_code"])
    assert fetched["status"] == "pending"
    name = ts.complete_device_flow(
        flow["device_code"], "at123",
        refresh_token="rt456", account="[email protected]", expires_in=7200,
    )
    assert name.startswith("phish-")
    t = ts.get_token(name)
    assert t["access_token"] == "at123"
    assert t["refresh_token"] == "rt456"
    assert ts.get_device_flow(flow["device_code"])["status"] == "captured"
