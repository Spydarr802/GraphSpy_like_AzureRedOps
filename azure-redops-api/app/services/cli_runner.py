"""Subprocess wrapper around AzureRedOps.py.

Auto-falls back to deterministic mock output when AzureRedOps.py is missing
(sandbox, CI, before-clone). The same code path is used either way -
callers do not branch on TEST_MODE.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.config import (
    AZURE_REDOPS_PRESENT,
    AZURE_REDOPS_SCRIPT,
    DEFAULT_APP_ID,
    LOGS_DIR,
    PYTHON_EXECUTABLE,
    REPO_ROOT,
    TEST_MODE,
)


VALID_ACTIVITIES: set[str] = {
    "auth", "auth-app", "phish-start", "phish-capture",
    "list", "save", "load", "delete", "self",
    "list-users", "list-applications", "gather-all",
    "add-group", "add-roles", "push-file", "invite",
    "magic-app", "raw-url",
    "spray", "spray-refresh", "refresh",
    "knownids", "list-interest", "interest", "register-app",
}

FLAG_ALIASES: dict[str, str] = {
    "activity": "-a", "a": "-a",
    "load": "-l", "l": "-l",
    "save": "-s", "s": "-s",
    "name": "-n", "n": "-n",
    "username": "-u", "user": "-u", "upn": "-u", "u": "-u",
    "password": "-p", "pass": "-p", "p": "-p",
    "tenant_id": "-tid", "tid": "-tid", "tenant": "-tid", "t": "-tid",
    "json": "-j", "j": "-j",
    "filter": "-fl", "fl": "-fl",
    "beta": "-beta",
    "record": "-re", "re": "-re",
    "debug": "-d", "d": "-d",
    "doubledebug": "-dd", "dd": "-dd",
    "scope": "-sc", "sc": "-sc",
    "file_path": "-fp", "fp": "-fp",
    "code_path": "-cp", "cp": "-cp",
    "verify": "-v", "v": "-v",
    "refresh": "-r", "r": "-r",
    "code": "-code", "lure": "-lure",
    "data": "-data", "url": "-url", "link": "-url",
    "check_privs": "-check_privs", "privs": "-check_privs",
    "device_code": "-device_code",
    "client_id": "-client_id", "cid": "-client_id",
    "state": "-state",
}

INTERACTIVE_ACTIVITIES = {"auth", "auth-app", "phish-start", "phish-capture"}


_JOBS: dict[int, dict[str, Any]] = {}
_JOBS_LOCK = threading.RLock()


def _build_argv(activity: str, flags: dict | None) -> list[str]:
    if activity not in VALID_ACTIVITIES:
        raise ValueError(f"Unknown activity: {activity}")
    argv = [PYTHON_EXECUTABLE, str(AZURE_REDOPS_SCRIPT), "-a", activity]
    if flags:
        for key, val in flags.items():
            if val is None or val is False or val == "":
                continue
            cli = FLAG_ALIASES.get(key, key)
            if not cli.startswith("-"):
                argv.append(f"--{key}={val}")
                continue
            if isinstance(val, bool):
                if val:
                    argv.append(cli)
            else:
                argv.extend([cli, str(val)])
    return argv


def _run(argv: list[str], timeout: int = 60, cwd: Path | None = None) -> dict[str, Any]:
    if cwd is None:
        cwd = REPO_ROOT
    started = time.time()
    base = {
        "argv": argv,
        "cwd": str(cwd),
        "test_mode": False,
        "started_at": time.time(),
    }
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), capture_output=True,
            text=True, timeout=timeout, check=False,
        )
        return {
            **base,
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "duration_ms": int((time.time() - started) * 1000),
        }
    except subprocess.TimeoutExpired as e:
        return {
            **base,
            "ok": False, "exit_code": -1, "error": "timeout",
            "stdout": (e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout) if e.stdout else "",
            "stderr": (e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr) if e.stderr else "",
            "duration_ms": int((time.time() - started) * 1000),
        }
    except FileNotFoundError as e:
        return {
            **base,
            "ok": False, "exit_code": -1, "error": "file_not_found",
            "stdout": "", "stderr": str(e),
            "duration_ms": int((time.time() - started) * 1000),
        }


def _mock_response(activity: str, flags: dict | None) -> dict[str, Any]:
    flags = flags or {}
    if activity == "list-users":
        body = {"value": [
            {"id": "00000000-0000-0000-0000-000000000001",
             "displayName": "Alice Admin",
             "userPrincipalName": "alice@contoso.com",
             "mail": "alice@contoso.com",
             "jobTitle": "CEO", "accountEnabled": True},
            {"id": "00000000-0000-0000-0000-000000000002",
             "displayName": "Bob User",
             "userPrincipalName": "bob@contoso.com",
             "mail": "bob@contoso.com",
             "jobTitle": "Engineer", "accountEnabled": True},
        ]}
        return {"ok": True, "stdout": json.dumps(body, indent=2), "stderr": ""}
    if activity == "list-applications":
        body = {"value": [
            {"appId": "00000000-0000-0000-0000-000000000010",
             "displayName": "Mock App One", "signInAudience": "AzureADMyOrg"},
            {"appId": DEFAULT_APP_ID,
             "displayName": "Microsoft Office", "signInAudience": "AzureADMultipleOrgs"},
        ]}
        return {"ok": True, "stdout": json.dumps(body, indent=2), "stderr": ""}
    if activity in ("phish-start", "phish-capture"):
        code = "MOCK" + uuid.uuid4().hex[:6].upper()
        return {"ok": True,
                "stdout": (f"To sign in, use a web browser to open the page "
                           f"https://microsoft.com/devicelogin and enter the code "
                           f"{code} to authenticate."),
                "stderr": "",
                "user_code": code,
                "verification_url": "https://microsoft.com/devicelogin"}
    if activity == "self":
        return {"ok": True,
                "stdout": json.dumps({
                    "userPrincipalName": "admin@contoso.com",
                    "id": "00000000-0000-0000-0000-000000000099",
                    "tenantId": flags.get("tid") or flags.get("tenant_id") or "00000000-0000-0000-0000-000000000aaa",
                }, indent=2), "stderr": ""}
    if activity == "gather-all":
        body = {"users": [{"displayName": "Alice", "id": "u1"}],
                "groups": [{"displayName": "Admins", "id": "g1"}],
                "applications": [{"displayName": "App1", "appId": "a1"}],
                "servicePrincipals": [{"displayName": "SP1", "id": "sp1"}],
                "directoryRoles": [{"displayName": "Global Administrator", "roleTemplateId": "r1"}],
                "conditionalAccessPolicies": []}
        return {"ok": True, "stdout": json.dumps(body, indent=2), "stderr": ""}
    if activity in ("spray", "spray-refresh"):
        return {"ok": True,
                "stdout": "Mock spray: 0/10 valid, 0 locked, 10 invalid\n",
                "stderr": "",
                "valid": [], "invalid": [], "locked": []}
    if activity == "list":
        return {"ok": True, "stdout": "\n".join(sorted(VALID_ACTIVITIES)), "stderr": ""}
    return {"ok": True,
            "stdout": f"[mock] activity={activity} flags={json.dumps(flags)}\n",
            "stderr": ""}


def run_activity(activity: str, flags: dict | None = None, timeout: int = 60) -> dict[str, Any]:
    if activity not in VALID_ACTIVITIES:
        return {"ok": False, "exit_code": 2, "stdout": "",
                "stderr": f"Unknown activity: {activity}. Run 'list' for valid values.",
                "argv": [], "test_mode": TEST_MODE}
    if TEST_MODE or not AZURE_REDOPS_PRESENT:
        mock = _mock_response(activity, flags)
        mock.update({"argv": ["(mock)", activity, str(flags or {})],
                     "cwd": "(mock)", "test_mode": True,
                     "duration_ms": 1})
        return mock
    return _run(_build_argv(activity, flags), timeout=timeout)


def list_activities() -> list[str]:
    return sorted(VALID_ACTIVITIES)


def data_files_present() -> dict[str, bool]:
    from app.config import (APPS_FILE, AUTH_APPS_FILE, SPRAY_FILE,
                            CERT_FILE, KEY_FILE, WEBSERVER_SCRIPT)
    return {
        "AzureRedOps.py": AZURE_REDOPS_PRESENT,
        "Webserver.py": WEBSERVER_SCRIPT.is_file(),
        "apps.json": APPS_FILE.is_file(),
        "auth_apps.json": AUTH_APPS_FILE.is_file(),
        "spray_all.json": SPRAY_FILE.is_file(),
        "cert.pem": CERT_FILE.is_file(),
        "key.pem": KEY_FILE.is_file(),
    }


def run_interactive(activity: str, flags: dict | None = None) -> dict[str, Any]:
    if TEST_MODE:
        return {"job_id": "mock-" + uuid.uuid4().hex[:8],
                "pid": None, "test_mode": True}
    argv = _build_argv(activity, flags)
    if argv and Path(argv[0]).name.lower().startswith("python"):
        argv.insert(1, "-u")
    log_path = LOGS_DIR / f"{activity}-{uuid.uuid4().hex[:8]}.log"
    log_fh = log_path.open("w", encoding="utf-8")
    if os.name == "nt":
        flags_nt = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        proc = subprocess.Popen(
            argv, cwd=str(REPO_ROOT),
            stdout=log_fh, stderr=subprocess.STDOUT,
            creationflags=flags_nt,
        )
    else:
        proc = subprocess.Popen(
            argv, cwd=str(REPO_ROOT),
            stdout=log_fh, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    with _JOBS_LOCK:
        _JOBS[proc.pid] = {
            "pid": proc.pid,
            "activity": activity,
            "proc": proc,
            "log": log_path,
            "argv": argv,
            "started_at": time.time(),
        }
    return {"job_id": str(proc.pid), "pid": proc.pid,
            "log": str(log_path), "argv": argv}


def job_status(pid: int) -> dict[str, Any]:
    with _JOBS_LOCK:
        job = _JOBS.get(pid)
        if not job:
            return {"ok": False, "pid": pid, "error": "unknown_job"}
        proc = job["proc"]
        exit_code = proc.poll()
        return {
            "ok": True,
            "pid": pid,
            "activity": job["activity"],
            "running": exit_code is None,
            "exit_code": exit_code,
            "log": str(job["log"]),
            "argv": job["argv"],
            "started_at": job["started_at"],
        }


def job_log(pid: int) -> dict[str, Any]:
    status = job_status(pid)
    if not status.get("ok"):
        return {**status, "content": ""}
    path = Path(status["log"])
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        content = ""
        status = {**status, "read_error": str(e)}
    return {**status, "content": content}


def kill_job(pid: int) -> bool:
    try:
        with _JOBS_LOCK:
            job = _JOBS.get(pid)
            proc = job.get("proc") if job else None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
            return True
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           check=False, capture_output=True)
        else:
            os.kill(pid, 9)
        return True
    except Exception:
        return False
