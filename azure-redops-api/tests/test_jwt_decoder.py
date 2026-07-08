"""Tests for the JWT decoder utility."""
import json
import base64
import time
from app.utils.jwt_decoder import decode_jwt


def _make_jwt(payload: dict, header: dict | None = None) -> str:
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    h = header or {"alg": "RS256", "typ": "JWT"}
    return f"{b64(h)}.{b64(payload)}.signature"


def test_decode_valid_jwt():
    token = _make_jwt({"sub": "[email protected]", "name": "Test", "exp": 9999999999})
    r = decode_jwt(token)
    assert r is not None
    assert r["header"]["alg"] == "RS256"
    assert r["payload"]["sub"] == "[email protected]"
    assert r["payload"]["name"] == "Test"
    assert r["signature_present"] is True
    assert r["is_expired"] is False


def test_decode_expired_jwt():
    token = _make_jwt({"sub": "old", "exp": int(time.time()) - 1000})
    r = decode_jwt(token)
    assert r["is_expired"] is True


def test_decode_invalid_token_returns_none():
    assert decode_jwt(None) is None
    assert decode_jwt("") is None
    assert decode_jwt("not-a-jwt") is None
    assert decode_jwt("only.two") is None


def test_decode_garbage_payload_falls_back_gracefully():
    # payload segment is not valid base64 -> returns empty payload dict
    token = "aaa.!!!.bbb"
    r = decode_jwt(token)
    assert r is not None
    assert r["header"] == {}
    assert r["payload"] == {}


def test_decode_expires_at_iso_parsed():
    token = _make_jwt({"exp": 1700000000})
    r = decode_jwt(token)
    assert r["expires_at_iso"] is not None
    assert r["expires_at_iso"].startswith("2023-")


def test_signature_present_marker():
    token = _make_jwt({"a": 1})
    r = decode_jwt(token)
    assert r["signature_present"] is True
