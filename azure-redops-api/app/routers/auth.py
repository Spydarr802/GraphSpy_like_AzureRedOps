"""Authentication endpoints: ROPC, device-code start, device-code capture.

Each endpoint shells out to AzureRedOps.py via cli_runner.run_activity().
Tokens that come back are persisted through token_store so subsequent
activities can reference them via the `-l <name>` flag.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import DEFAULT_APP_ID, DEFAULT_TENANT_ID
from app.services import cli_runner, output_parser
from app.utils import token_store, jwt_decoder

router = APIRouter(prefix="/auth", tags=["Authentication"])


class ROPCIn(BaseModel):
    username: str
    password: str
    tenant_id: Optional[str] = DEFAULT_TENANT_ID
    client_id: Optional[str] = DEFAULT_APP_ID
    scope: Optional[str] = "https://graph.microsoft.com/.default openid profile offline_access"
    save_as: Optional[str] = None


class DeviceStartIn(BaseModel):
    client_id: Optional[str] = DEFAULT_APP_ID
    tenant_id: Optional[str] = DEFAULT_TENANT_ID
    scope: Optional[str] = "https://graph.microsoft.com/.default openid profile offline_access"
    save_as: Optional[str] = None


class DeviceCaptureIn(BaseModel):
    user_code: str
    device_code: Optional[str] = None
    save_as: Optional[str] = None


@router.post("/ropc")
def ropc_auth(req: ROPCIn):
    """Resource Owner Password Credentials via AzureRedOps.py -a auth."""
    flags = {
        "u": req.username,
        "p": req.password,
        "tid": req.tenant_id,
        "scope": req.scope,
    }
    if req.client_id and req.client_id != DEFAULT_APP_ID:
        flags["client_id"] = req.client_id

    result = cli_runner.run_activity("auth", flags=flags, timeout=90)
    parsed = output_parser.parse("auth", result)

    cap = parsed.get("capture") or {}
    token_name = req.save_as
    if cap.get("access_token"):
        token_name = token_name or f"ropc-{req.username.split('@')[0]}"
        token_store.save_token(token_name, {
            "access_token": cap["access_token"],
            "refresh_token": cap.get("refresh_token"),
            "id_token": cap.get("id_token"),
            "scope": cap.get("scope") or req.scope,
            "client_id": req.client_id,
            "tenant_id": cap.get("tenant_id") or req.tenant_id,
            "account": req.username,
            "account_type": "Microsoft",
            "expires_in": cap.get("expires_in") or 3600,
        })
        parsed["token_name"] = token_name
        parsed["saved"] = True
    return {
        "ok": parsed.get("ok", False),
        "test_mode": parsed.get("test_mode", False),
        "username": req.username,
        "tenant_id": req.tenant_id,
        "client_id": req.client_id,
        "argv": parsed.get("argv"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "errors": parsed.get("errors", []),
        "capture": parsed.get("capture") or {},
        "token_name": token_name,
        "decoded": (jwt_decoder.decode_jwt(cap.get("access_token"))
                    if cap.get("access_token") else None),
    }


@router.post("/device/start")
def device_start(req: DeviceStartIn):
    """Kick off an AzureRedOps device-code flow (-a phish-start)."""
    flags = {
        "scope": req.scope,
        "tid": req.tenant_id,
    }
    if req.client_id and req.client_id != DEFAULT_APP_ID:
        flags["client_id"] = req.client_id

    result = cli_runner.run_activity("phish-start", flags=flags, timeout=30)
    parsed = output_parser.parse("phish-start", result)
    parsed_stdout = parsed.get("parsed") or {}

    user_code = ((parsed_stdout.get("user_codes") or [None])[0])
    verification_url = parsed_stdout.get("verification_url")

    stored = token_store.start_device_capture(
        session_email="",
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
        "tenant_id": req.tenant_id,
        "client_id": req.client_id,
        "scope": req.scope,
    }


@router.post("/device/capture")
def device_capture(req: DeviceCaptureIn):
    """Poll AzureRedOps.py -a phish-capture with a user code to grab the token."""
    flags = {"code": req.user_code}
    if req.device_code:
        flags["device_code"] = req.device_code

    result = cli_runner.run_activity("phish-capture", flags=flags, timeout=60)
    parsed = output_parser.parse("phish-capture", result)
    cap = parsed.get("capture") or {}

    token_name = None
    if cap.get("access_token"):
        token_name = req.save_as or f"phish-{req.user_code.lower()}"
        token_store.save_token(token_name, {
            "access_token": cap["access_token"],
            "refresh_token": cap.get("refresh_token"),
            "id_token": cap.get("id_token"),
            "scope": cap.get("scope"),
            "client_id": cap.get("client_id"),
            "tenant_id": cap.get("tenant_id"),
            "account": cap.get("user_principal_name"),
            "account_type": "Microsoft",
            "expires_in": cap.get("expires_in") or 3600,
        })
        if req.device_code:
            token_store.complete_device_flow(
                req.device_code, cap["access_token"],
                refresh_token=cap.get("refresh_token"),
                id_token=cap.get("id_token"),
                scope=cap.get("scope"),
                account=cap.get("user_principal_name"),
            )

    return {
        "ok": parsed.get("ok", False),
        "test_mode": parsed.get("test_mode", False),
        "argv": parsed.get("argv"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "errors": parsed.get("errors", []),
        "user_code": req.user_code,
        "capture": parsed.get("capture"),
        "token_name": token_name,
        "decoded": (jwt_decoder.decode_jwt(cap.get("access_token"))
                    if cap.get("access_token") else None),
    }


@router.post("/self")
def self_inspect(token_name: str):
    """Look up the calling identity using a saved token (-a self -l <name>)."""
    flags = {"load": token_name}
    result = cli_runner.run_activity("self", flags=flags, timeout=30)
    parsed = output_parser.parse("self", result)
    return {
        "ok": parsed.get("ok", False),
        "test_mode": parsed.get("test_mode", False),
        "token_name": token_name,
        "argv": parsed.get("argv"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "errors": parsed.get("errors", []),
        "capture": parsed.get("capture"),
    }