"""Manages the lifespan of Webserver.py (the phishing TLS server).

Uses Popen + non-blocking poll. State is exposed via `status()` so the
backend can report whether the server is running, its PID, and its log path.
"""
from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.config import (
    CERT_DIR, CERT_FILE, KEY_FILE, LOGS_DIR,
    PHISH_HOST, PHISH_PORT, PYTHON_EXECUTABLE, REPO_ROOT, TEST_MODE,
    WEBSERVER_SCRIPT,
)


class _State:
    proc: subprocess.Popen | None = None
    log_path: Path | None = None
    pid: int | None = None
    started_at: float | None = None
    host: str = PHISH_HOST
    port: int = PHISH_PORT


_STATE = _State()
_LOCK = threading.RLock()


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def status() -> dict[str, Any]:
    with _LOCK:
        alive = _STATE.proc is not None and _STATE.proc.poll() is None
        if _STATE.proc is not None and not alive:
            _STATE.proc = None
            _STATE.pid = None
        return {
            "running": alive,
            "pid": _STATE.pid,
            "host": _STATE.host,
            "port": _STATE.port,
            "log": str(_STATE.log_path) if _STATE.log_path else None,
            "started_at": _STATE.started_at,
            "webserver_present": WEBSERVER_SCRIPT.is_file(),
            "cert_present": CERT_FILE.is_file() and KEY_FILE.is_file(),
            "test_mode": TEST_MODE,
        }


def start(host: str | None = None, port: int | None = None) -> dict[str, Any]:
    with _LOCK:
        if _STATE.proc is not None and _STATE.proc.poll() is None:
            return {"ok": False, "error": "already_running", "status": status()}

        if TEST_MODE or not WEBSERVER_SCRIPT.is_file():
            return {"ok": True, "test_mode": True,
                    "message": "mock: webserver not started",
                    "status": {**status(), "running": True,
                               "pid": 99999, "host": host or PHISH_HOST,
                               "port": port or PHISH_PORT}}

        if not (CERT_FILE.is_file() and KEY_FILE.is_file()):
            return {"ok": False, "error": "missing_certs",
                    "cert": str(CERT_FILE), "key": str(KEY_FILE)}

        _STATE.host = host or PHISH_HOST
        _STATE.port = port or PHISH_PORT
        log_path = LOGS_DIR / f"webserver-{uuid.uuid4().hex[:8]}.log"
        log_fh = log_path.open("w", encoding="utf-8")
        argv = [PYTHON_EXECUTABLE, str(WEBSERVER_SCRIPT),
                "--host", _STATE.host, "--port", str(_STATE.port)]
        try:
            _STATE.proc = subprocess.Popen(
                argv, cwd=str(REPO_ROOT),
                stdout=log_fh, stderr=subprocess.STDOUT,
            )
        except OSError as e:
            return {"ok": False, "error": "spawn_failed", "detail": str(e)}
        _STATE.log_path = log_path
        _STATE.pid = _STATE.proc.pid
        _STATE.started_at = time.time()

        deadline = time.time() + 5
        while time.time() < deadline:
            if _port_open(_STATE.host, _STATE.port, 0.3):
                break
            time.sleep(0.2)
        return {"ok": True, "status": status()}


def stop() -> dict[str, Any]:
    with _LOCK:
        if _STATE.proc is None or _STATE.proc.poll() is not None:
            _STATE.proc = None
            _STATE.pid = None
            return {"ok": True, "already_stopped": True, "status": status()}
        try:
            _STATE.proc.terminate()
            try:
                _STATE.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _STATE.proc.kill()
                _STATE.proc.wait(timeout=2)
        finally:
            _STATE.proc = None
            _STATE.pid = None
            _STATE.started_at = None
        return {"ok": True, "status": status()}


def reload_certs() -> dict[str, Any]:
    if not (CERT_FILE.is_file() and KEY_FILE.is_file()):
        return {"ok": False, "error": "missing_certs"}
    return {"ok": True, "cert": str(CERT_FILE), "key": str(KEY_FILE),
            "cert_dir": str(CERT_DIR)}