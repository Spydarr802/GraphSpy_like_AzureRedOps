"""Central configuration: locates AzureRedOps assets and backend state dirs.

Resolution order (first match wins):
  - $AZR_REPO_ROOT env var if set
  - REPO_ROOT derived from app/config.py location (../..)
  - sandbox fallback at /home/user/azure-redops-stack/azure-redops-api

Data files (WebServer.py, apps.json, etc.) are looked up first at repo root,
then at includes/ - whichever exists.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _detect_repo_root() -> Path:
    env_root = os.getenv("AZR_REPO_ROOT")
    if env_root:
        p = Path(env_root).resolve()
        if p.is_dir() and (p / "AzureRedOps.py").is_file():
            return p
    here = Path(__file__).resolve().parent.parent
    candidate = here.parent
    if (candidate / "AzureRedOps.py").is_file():
        return candidate
    sandbox = Path("/home/user/azure-redops-stack/azure-redops-api")
    return sandbox.parent if (sandbox.parent / "AzureRedOps.py").is_file() else sandbox


REPO_ROOT: Path = _detect_repo_root()
APP_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = APP_ROOT / "data"
TOKEN_DIR: Path = DATA_DIR / "tokens"
CAPTURE_DIR: Path = DATA_DIR / "captures"
LOGS_DIR: Path = DATA_DIR / "logs"
for _d in (DATA_DIR, TOKEN_DIR, CAPTURE_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _find_python() -> str:
    for cand in (
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "bin" / "python",
        Path(sys.executable),
    ):
        if cand.is_file():
            return str(cand)
    return sys.executable


PYTHON_EXECUTABLE = _find_python()

AZURE_REDOPS_SCRIPT: Path = REPO_ROOT / "AzureRedOps.py"
INCLUDES_DIR: Path = REPO_ROOT / "includes"


def _first_existing(*candidates: Path) -> Path:
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0] if candidates else REPO_ROOT


WEBSERVER_SCRIPT: Path = _first_existing(REPO_ROOT / "WebServer.py",
                                          INCLUDES_DIR / "WebServer.py")
APPS_FILE: Path = _first_existing(REPO_ROOT / "apps.json",
                                  INCLUDES_DIR / "apps.json")
AUTH_APPS_FILE: Path = _first_existing(REPO_ROOT / "auth_apps.json",
                                       INCLUDES_DIR / "auth_apps.json")
SPRAY_FILE: Path = _first_existing(REPO_ROOT / "spray_all.json",
                                   INCLUDES_DIR / "spray_all.json")
CERT_DIR: Path = INCLUDES_DIR / "web"
CERT_FILE: Path = CERT_DIR / "cert.pem"
KEY_FILE: Path = CERT_DIR / "key.pem"

AZURE_REDOPS_PRESENT: bool = AZURE_REDOPS_SCRIPT.is_file()
TEST_MODE: bool = not AZURE_REDOPS_PRESENT

DEFAULT_APP_ID = "d3590ed6-52b3-4102-aeff-aad2292ab01c"
ALT_APP_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
DEFAULT_TENANT_ID = "common"

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_ORIGINS = [
    o.strip() for o in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",") if o.strip()
]

PHISH_HOST = os.getenv("PHISH_HOST", "0.0.0.0")
PHISH_PORT = int(os.getenv("PHISH_PORT", "8443"))