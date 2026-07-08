"""Password spray endpoints. Shells out to AzureRedOps.py -a spray."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import SPRAY_FILE, TEST_MODE
from app.services import cli_runner, output_parser

router = APIRouter(prefix="/spray", tags=["Spraying"])


class SprayIn(BaseModel):
    username: str
    password: str
    tenant_id: Optional[str] = "common"
    check_privs: bool = False
    refresh: bool = False
    timeout: int = 120


@router.get("/list")
def spray_list():
    """Read spray_all.json from disk."""
    if not SPRAY_FILE.is_file():
        return {"present": False, "count": 0, "users": []}
    try:
        with SPRAY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(500, f"failed to read spray_all.json: {e}")
    users = data if isinstance(data, list) else []
    return {
        "present": True,
        "count": len(users),
        "users": users,
        "path": str(SPRAY_FILE),
    }


@router.post("/")
def run_spray(req: SprayIn):
    """Run AzureRedOps.py -a spray (or spray-refresh)."""
    flags = {
        "u": req.username,
        "p": req.password,
        "tid": req.tenant_id,
    }
    if req.check_privs:
        flags["check_privs"] = True
    activity = "spray-refresh" if req.refresh else "spray"

    result = cli_runner.run_activity(activity, flags=flags, timeout=req.timeout)
    parsed = output_parser.parse(activity, result)
    return {
        "ok": parsed.get("ok", False),
        "test_mode": parsed.get("test_mode", False),
        "activity": activity,
        "username": req.username,
        "tenant_id": req.tenant_id,
        "check_privs": req.check_privs,
        "argv": parsed.get("argv"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "errors": parsed.get("errors", []),
        "spray_result": parsed.get("spray_result"),
        "summary": parsed.get("summary"),
    }


@router.post("/file")
def spray_file(timeout: int = 300):
    """Run -a spray reading targets from spray_all.json (-u $(jq spray_all.json))."""
    if not SPRAY_FILE.is_file():
        raise HTTPException(404, f"spray_all.json not found at {SPRAY_FILE}")
    flags = {"data": str(SPRAY_FILE)}
    result = cli_runner.run_activity("spray", flags=flags, timeout=timeout)
    parsed = output_parser.parse("spray", result)
    return {
        "ok": parsed.get("ok", False),
        "test_mode": parsed.get("test_mode", False),
        "argv": parsed.get("argv"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "errors": parsed.get("errors", []),
        "spray_result": parsed.get("spray_result"),
        "summary": parsed.get("summary"),
    }