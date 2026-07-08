"""Saved token CRUD + JWT decode endpoints.

Tokens are stored via token_store. Decoding is done by jwt_decoder.
Refresh goes through AzureRedOps.py -a refresh when TEST_MODE is off.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import cli_runner, output_parser
from app.utils import token_store, jwt_decoder

router = APIRouter(prefix="/tokens", tags=["Tokens"])


class SaveIn(BaseModel):
    name: str
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None
    client_id: Optional[str] = None
    tenant_id: Optional[str] = None
    account: Optional[str] = None
    account_type: Optional[str] = "Microsoft"
    expires_in: Optional[int] = 3600


class DecodeRawIn(BaseModel):
    token: str


class RefreshIn(BaseModel):
    name: str


@router.get("/")
def list_tokens():
    return {"tokens": token_store.list_tokens()}


@router.post("/save")
def save(req: SaveIn):
    return token_store.save_token(req.name, req.model_dump())


@router.delete("/{name}")
def delete(name: str):
    return token_store.delete_token(name)


@router.get("/{name}/raw")
def raw(name: str):
    t = token_store.get_token(name)
    if not t:
        raise HTTPException(404, "token not found")
    return t


@router.get("/{name}/access")
def access(name: str):
    t = token_store.get_token(name)
    if not t:
        raise HTTPException(404, "token not found")
    return {"access_token": t.get("access_token")}


@router.get("/{name}/decode")
def decode(name: str):
    t = token_store.get_token(name)
    if not t:
        raise HTTPException(404, "token not found")
    return jwt_decoder.decode_jwt(t.get("access_token")) or {"error": "invalid token"}


@router.post("/decode-raw")
def decode_raw(req: DecodeRawIn):
    return jwt_decoder.decode_jwt(req.token) or {"error": "invalid token"}


@router.post("/{name}/refresh")
def refresh(req: RefreshIn):
    """Refresh a saved token by shelling out to AzureRedOps.py -a refresh -l <name>."""
    t = token_store.get_token(req.name)
    if not t:
        raise HTTPException(404, "token not found")
    if not t.get("refresh_token"):
        raise HTTPException(400, "no refresh_token stored for this entry")

    flags = {"load": req.name}
    result = cli_runner.run_activity("refresh", flags=flags, timeout=60)
    parsed = output_parser.parse("refresh", result)
    cap = parsed.get("capture") or {}

    if cap.get("access_token"):
        token_store.save_token(req.name, {
            **t,
            "access_token": cap["access_token"],
            "refresh_token": cap.get("refresh_token") or t.get("refresh_token"),
            "id_token": cap.get("id_token") or t.get("id_token"),
            "expires_in": cap.get("expires_in") or t.get("expires_in"),
        })
        return {
            "ok": True,
            "name": req.name,
            "test_mode": parsed.get("test_mode", False),
            "capture": cap,
            "decoded": jwt_decoder.decode_jwt(cap["access_token"]),
        }

    return {
        "ok": parsed.get("ok", False),
        "name": req.name,
        "test_mode": parsed.get("test_mode", False),
        "argv": parsed.get("argv"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "errors": parsed.get("errors", []),
        "note": "refresh did not return a new access_token",
    }