"""Activity runner: shells out to AzureRedOps.py for every CLI activity.

Every endpoint goes through cli_runner.run_activity() which:
  - Uses subprocess.run([python, AzureRedOps.py, -a, activity, ...flags])
    when AzureRedOps.py is present (LIVE mode)
  - Returns deterministic mock JSON when it's missing (TEST mode)

The frontend never branches on TEST_MODE; the same shape is returned either way.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import (
    AZURE_REDOPS_PRESENT, TEST_MODE,
    AZURE_REDOPS_SCRIPT,
    DEFAULT_APP_ID, ALT_APP_ID,
)
from app.services import cli_runner, output_parser, webserver_manager

router = APIRouter(prefix="/activities", tags=["Activities"])


class ActivityRequest(BaseModel):
    activity: str
    token_name: Optional[str] = None
    flags: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 60


class InteractiveRequest(BaseModel):
    activity: str
    flags: Optional[Dict[str, Any]] = None


@router.get("")
@router.get("/")
def list_activities():
    """List every valid CLI activity + runtime state."""
    return {
        "activities": cli_runner.list_activities(),
        "count": len(cli_runner.VALID_ACTIVITIES),
        "interactive": sorted(cli_runner.INTERACTIVE_ACTIVITIES),
        "test_mode": TEST_MODE,
        "azure_redops_present": AZURE_REDOPS_PRESENT,
        "script_path": str(AZURE_REDOPS_SCRIPT),
        "default_app_id": DEFAULT_APP_ID,
        "alt_app_id": ALT_APP_ID,
        "data_files": cli_runner.data_files_present(),
    }


@router.post("/run")
def run(req: ActivityRequest):
    """Run any CLI activity through AzureRedOps.py."""
    if req.activity not in cli_runner.VALID_ACTIVITIES:
        raise HTTPException(
            400,
            f"Unknown activity '{req.activity}'. "
            f"Valid: {sorted(cli_runner.VALID_ACTIVITIES)}",
        )

    flags: dict[str, Any] = dict(req.flags or {})
    if req.token_name and "load" not in flags and "l" not in flags:
        flags["load"] = req.token_name

    result = cli_runner.run_activity(req.activity, flags=flags,
                                     timeout=req.timeout or 60)
    parsed = output_parser.parse(req.activity, result)
    return {
        "ok": parsed.get("ok", False),
        "activity": req.activity,
        "test_mode": parsed.get("test_mode", False),
        "exit_code": parsed.get("exit_code"),
        "argv": parsed.get("argv"),
        "duration_ms": parsed.get("duration_ms"),
        "stdout": parsed.get("stdout", ""),
        "stderr": parsed.get("stderr", ""),
        "stdout_clean": parsed.get("stdout_clean"),
        "parsed": parsed.get("parsed"),
        "summary": parsed.get("summary"),
        "errors": parsed.get("errors", []),
        "users": parsed.get("users"),
        "applications": parsed.get("applications"),
        "items": parsed.get("items"),
        "dump": parsed.get("dump"),
        "capture": parsed.get("capture"),
        "spray_result": parsed.get("spray_result"),
        "known_ids": parsed.get("known_ids"),
        "files": parsed.get("files"),
        "roles": parsed.get("roles"),
    }


@router.post("/interactive")
def interactive(req: InteractiveRequest):
    """Launch an interactive CLI activity in the background."""
    if req.activity not in cli_runner.INTERACTIVE_ACTIVITIES:
        raise HTTPException(
            400,
            f"Activity '{req.activity}' is not interactive. "
            f"Valid interactive: {sorted(cli_runner.INTERACTIVE_ACTIVITIES)}",
        )
    return cli_runner.run_interactive(req.activity, req.flags)


@router.delete("/job/{pid}")
def kill(pid: int):
    ok = cli_runner.kill_job(pid)
    return {"ok": ok, "pid": pid}


@router.get("/jobs")
def list_jobs():
    return {
        "webserver": webserver_manager.status(),
        "test_mode": TEST_MODE,
    }


@router.get("/job/{pid}")
def job_status(pid: int):
    status = cli_runner.job_status(pid)
    if not status.get("ok"):
        raise HTTPException(404, status.get("error", "unknown_job"))
    return status


@router.get("/job/{pid}/log")
def job_log(pid: int):
    status = cli_runner.job_log(pid)
    if not status.get("ok"):
        raise HTTPException(404, status.get("error", "unknown_job"))
    return status


@router.post("/parse")
def parse_only(req: ActivityRequest):
    """Run the parser on raw stdout WITHOUT invoking the CLI."""
    synthetic = {
        "ok": True,
        "stdout": req.flags.get("__stdout", "") if req.flags else "",
        "test_mode": True,
    }
    parsed = output_parser.parse(req.activity, synthetic)
    return {
        "activity": req.activity,
        "parsed": parsed.get("parsed"),
        "summary": parsed.get("summary"),
        "users": parsed.get("users"),
        "applications": parsed.get("applications"),
        "capture": parsed.get("capture"),
    }
