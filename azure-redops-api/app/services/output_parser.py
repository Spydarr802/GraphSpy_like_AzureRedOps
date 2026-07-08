"""Parses AzureRedOps CLI stdout into structured data."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

import base64

# ---------- regex patterns ---------------------------------------------------

JWT_RE = re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')
ACCESS_TOKEN_RE = re.compile(r'(?im)^(?:access_token|accessToken|Access Token)\s*[:=]\s*"?([A-Za-z0-9._-]+)"?')
REFRESH_TOKEN_RE = re.compile(r'(?im)^(?:refresh_token|refreshToken|Refresh Token)\s*[:=]\s*"?([A-Za-z0-9._-]+)"?')
ID_TOKEN_RE = re.compile(r'(?im)^(?:id_token|idToken|ID Token)\s*[:=]\s*"?([A-Za-z0-9._-]+)"?')
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
TENANT_ID_RE = re.compile(r'(?i)(?:tenant[_-]?id|tid)\s*[:=]?\s*"?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"?')
USER_ID_RE = re.compile(r'(?i)(?:user[_-]?id|uid|objectid)\s*[:=]?\s*"?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"?')
APP_ID_RE = re.compile(r'(?i)(?:app[_-]?id|application[_-]?id|client[_-]?id)\s*[:=]?\s*"?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"?')
USER_CODE_RE = re.compile(r'\b([A-Z][A-Z0-9]{6,8})\b')
ROLE_NAME_RE = re.compile(r'(?i)\b(?:role|directory[_-]?role)\s*[:=]?\s*"?([A-Z][A-Za-z][\w\s-]{2,60})"?')
URL_RE = re.compile(r'https?://[^\s\'"<>)]+')
DEVICE_CODE_RE = re.compile(r'(?i)device[_\s-]*code["\s:=]+([A-Za-z0-9_-]+)')
EXPIRES_IN_RE = re.compile(r'(?i)expires[_\s-]*in["\s:=]+(\d+)')
INTERVAL_RE = re.compile(r'(?i)interval["\s:=]+(\d+)')

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
_ERROR_LINE = re.compile(r'^\s*(?:error|ERROR|ERROR:|ERROR\s)\s*[:\-]?\s*(.+)$')
_WARN_LINE = re.compile(r'^\s*(?:warning|WARN|WARNING:)\s*[:\-]?\s*(.+)$')
_HTTP_ERROR = re.compile(r'\b(\d{3})\s+(Forbidden|Unauthorized|Bad Request|Not Found|Too Many Requests|Internal Server Error)\b')

_GROUP_ID = re.compile(r'(?:group[_-]?id|objectId)["\s:]+([0-9a-f-]{36})', re.I)
_KNOWN_IDS_HEADER = re.compile(r'^\s*(id|upn|user|target|principal)\s+(type|kind)\s+', re.I)
_FILE_LINE = re.compile(r'\[FILE\]\s+(.+?)\s+\(([0-9]+)\s+bytes\)')
_VERSION_LINE = re.compile(r'(?:AzureRedOps|Azure RedOps|Version)\s*v?(\d+\.\d+\.\d+)', re.I)


# ---------- low-level stdout parsing -----------------------------------------

def _extract_json_objects(text: str) -> list[Any]:
    """Greedy depth-counted JSON object/array extraction from a text blob."""
    objs = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch not in ('{', '['):
            i += 1
            continue
        opener, closer = (('{', '}') if ch == '{' else ('[', ']'))
        depth, start, in_str, escape = 0, i, False, False
        for j in range(i, n):
            c = text[j]
            if in_str:
                if escape:
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
                continue
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    chunk = text[start:j + 1]
                    try:
                        objs.append(json.loads(chunk))
                    except json.JSONDecodeError:
                        pass
                    i = j
                    break
        else:
            break
        i += 1
    return objs


def parse_stdout(stdout: str) -> dict[str, Any]:
    """Parse AzureRedOps stdout into a structured dict.

    Returns {lines, json_objects, tokens, emails, tenant_ids, user_ids,
    app_ids, user_codes, role_names, verification_url, access_token,
    refresh_token, id_token}.
    """
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    json_objects = _extract_json_objects(stdout)
    tokens = list(dict.fromkeys(JWT_RE.findall(stdout)))
    emails = list(dict.fromkeys(EMAIL_RE.findall(stdout)))
    tenant_ids = list(dict.fromkeys(TENANT_ID_RE.findall(stdout)))
    user_ids = list(dict.fromkeys(USER_ID_RE.findall(stdout)))
    app_ids = list(dict.fromkeys(APP_ID_RE.findall(stdout)))
    role_names = list(dict.fromkeys(ROLE_NAME_RE.findall(stdout)))
    urls = URL_RE.findall(stdout)
    verification_url = next((u for u in urls if 'device' in u.lower() or 'login' in u.lower()), None)
    user_codes = USER_CODE_RE.findall(stdout)
    return {
        "lines": lines,
        "json_objects": json_objects,
        "tokens": tokens,
        "emails": emails,
        "tenant_ids": tenant_ids,
        "user_ids": user_ids,
        "app_ids": app_ids,
        "user_codes": user_codes,
        "role_names": role_names,
        "verification_url": verification_url,
        "access_token": _first(ACCESS_TOKEN_RE.findall(stdout)),
        "refresh_token": _first(REFRESH_TOKEN_RE.findall(stdout)),
        "id_token": _first(ID_TOKEN_RE.findall(stdout)),
    }


def _first(seq):
    return seq[0] if seq else None


def load_json_output(path: str | Path) -> Optional[dict]:
    p = Path(path)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


# ---------- entity extractors -----------------------------------------------

def extract_users(parsed: dict) -> list:
    out, seen = [], set()
    for obj in parsed.get("json_objects", []):
        cands = _candidates(obj)
        for c in cands:
            uid = c.get("id") or c.get("userPrincipalName")
            if not uid or uid in seen:
                continue
            seen.add(uid)
            out.append({
                "id": c.get("id"),
                "userPrincipalName": c.get("userPrincipalName") or c.get("mail"),
                "displayName": c.get("displayName"),
                "mail": c.get("mail") or c.get("userPrincipalName"),
                "jobTitle": c.get("jobTitle"),
                "department": c.get("department"),
                "accountEnabled": c.get("accountEnabled"),
                "userType": c.get("userType"),
                "lastSignInDateTime": c.get("signInActivity", {}).get("lastSignInDateTime") if isinstance(c.get("signInActivity"), dict) else c.get("lastSignInDateTime"),
            })
    return out


def extract_applications(parsed: dict) -> list:
    out, seen = [], set()
    for obj in parsed.get("json_objects", []):
        cands = _candidates(obj)
        for c in cands:
            aid = c.get("appId") or c.get("id")
            if not aid or aid in seen:
                continue
            seen.add(aid)
            out.append({
                "appId": c.get("appId"),
                "id": c.get("id"),
                "displayName": c.get("displayName"),
                "signInAudience": c.get("signInAudience"),
                "publisherDomain": c.get("publisherDomain"),
                "createdDateTime": c.get("createdDateTime"),
                "requiredResourceAccess": c.get("requiredResourceAccess"),
                "appRoles": c.get("appRoles"),
                "web": c.get("web"),
                "spa": c.get("spa"),
            })
    return out


def extract_groups(parsed: dict) -> list:
    out, seen = [], set()
    for obj in parsed.get("json_objects", []):
        cands = _candidates(obj)
        for c in cands:
            gid = c.get("id") or c.get("objectId")
            if not gid or gid in seen:
                continue
            seen.add(gid)
            out.append({
                "id": gid,
                "displayName": c.get("displayName") or c.get("name"),
                "description": c.get("description"),
                "securityEnabled": c.get("securityEnabled"),
                "mailEnabled": c.get("mailEnabled"),
                "isAssignableToRole": c.get("isAssignableToRole"),
            })
    return out


def extract_service_principals(parsed: dict) -> list:
    out, seen = [], set()
    for obj in parsed.get("json_objects", []):
        cands = _candidates(obj)
        for c in cands:
            spid = c.get("appId") or c.get("id")
            if not spid or spid in seen:
                continue
            seen.add(spid)
            out.append({
                "appId": spid,
                "id": c.get("id"),
                "displayName": c.get("displayName"),
                "servicePrincipalType": c.get("servicePrincipalType"),
                "publisherName": c.get("publisherName"),
                "accountEnabled": c.get("accountEnabled"),
            })
    return out


def extract_directory_roles(parsed: dict) -> list:
    out, seen = [], set()
    for obj in parsed.get("json_objects", []):
        cands = _candidates(obj)
        for c in cands:
            rid = c.get("roleTemplateId") or c.get("id")
            name = c.get("displayName") or c.get("name")
            if not rid or not name or rid in seen:
                continue
            seen.add(rid)
            out.append({
                "roleId": rid,
                "displayName": name,
                "description": c.get("description"),
                "isBuiltIn": c.get("isBuiltIn", True),
                "isEnabled": c.get("isEnabled", True),
            })
    return out


def extract_conditional_access_policies(parsed: dict) -> list:
    out, seen = [], set()
    for obj in parsed.get("json_objects", []):
        cands = _candidates(obj)
        for c in cands:
            pid = c.get("id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            out.append({
                "id": pid,
                "displayName": c.get("displayName"),
                "state": c.get("state"),
                "conditions": c.get("conditions"),
                "grantControls": c.get("grantControls"),
                "sessionControls": c.get("sessionControls"),
            })
    return out


def extract_interest(parsed: dict) -> list:
    items = []
    for obj in parsed.get("json_objects", []):
        if isinstance(obj, list):
            for c in obj:
                if isinstance(c, dict):
                    items.append(c)
        elif isinstance(obj, dict):
            items.append(obj)
    return items


def extract_files(parsed: dict) -> list:
    out = []
    for line in parsed.get("lines", []):
        m = _FILE_LINE.search(line)
        if m:
            out.append({"name": m.group(1), "size": int(m.group(2)), "raw": line})
    return out


def _candidates(obj: Any) -> list:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("value", "items", "users", "applications", "groups",
                    "servicePrincipals", "roles", "policies", "members"):
            if isinstance(obj.get(key), list):
                return obj[key]
        return [obj]
    return []


# ---------- device code & phish capture --------------------------------------

def parse_device_code(parsed: dict) -> dict:
    user_code, device_code, verification_url, expires_in, interval = (
        None, None, None, None, None,
    )
    for line in parsed.get("lines", []):
        m = re.search(r'code\s+([A-Z][A-Z0-9]{6,8})', line)
        if m and not user_code:
            user_code = m.group(1)
        m = re.search(r'(https?://\S*devicelogin\S*)', line, re.I)
        if m and not verification_url:
            verification_url = m.group(1)
        m = DEVICE_CODE_RE.search(line)
        if m and not device_code:
            device_code = m.group(1)
        m = EXPIRES_IN_RE.search(line)
        if m and not expires_in:
            try:
                expires_in = int(m.group(1))
            except ValueError:
                pass
        m = INTERVAL_RE.search(line)
        if m and not interval:
            try:
                interval = int(m.group(1))
            except ValueError:
                pass
    complete = (f"{verification_url}?otc={user_code}"
                if user_code and verification_url else verification_url)
    return {
        "user_code": user_code,
        "device_code": device_code,
        "verification_url": verification_url,
        "verification_uri_complete": complete,
        "expires_in": expires_in,
        "interval": interval,
        "message": " ".join(parsed.get("lines", [])[:6]),
    }


def wait_for_token_file(path: str | Path, timeout: int = 120,
                        poll: float = 2.0) -> Optional[dict]:
    from app.config import REPO_ROOT
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / path
    deadline = time.time() + timeout
    while time.time() < deadline:
        if p.exists():
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        time.sleep(poll)
    return None


def extract_phish_capture(parsed: dict) -> dict:
    capture = {"access_token": None, "refresh_token": None,
               "id_token": None, "client_info": None, "scope": None,
               "expires_in": None, "user_principal_name": None,
               "tenant_id": None}
    for obj in parsed.get("json_objects", []):
        if not isinstance(obj, dict):
            continue
        for key in ("access_token", "refresh_token", "id_token",
                    "client_info", "scope", "expires_in"):
            if obj.get(key):
                capture[key] = obj[key]
        upn = obj.get("userPrincipalName")
        if upn:
            capture["user_principal_name"] = upn
        tid = obj.get("tid") or obj.get("tenantId")
        if tid:
            capture["tenant_id"] = tid
    if not capture["access_token"] and parsed.get("tokens"):
        capture["access_token"] = parsed["tokens"][0]
    return capture


def parse_spray_result(parsed: dict) -> dict:
    out = {"valid": [], "invalid": [], "locked": [], "unknown": []}
    for line in parsed.get("lines", []):
        l = line.lower()
        email = parsed["emails"][0] if parsed.get("emails") else None
        if "successful" in l or "valid" in l or "password works" in l:
            out["valid"].append({"target": email, "detail": line})
        elif "locked" in l or "account locked" in l:
            out["locked"].append({"target": email, "detail": line})
        elif "invalid" in l or "wrong password" in l or "incorrect" in l:
            out["invalid"].append({"target": email, "detail": line})
        else:
            out["unknown"].append({"target": email, "detail": line})
    return out


def parse_known_ids_table(parsed: dict) -> list:
    rows, headers = [], None
    for line in parsed.get("lines", []):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("=="):
            continue
        if headers is None and _KNOWN_IDS_HEADER.search(stripped):
            headers = stripped.split()
            continue
        if headers is None:
            continue
        parts = stripped.split(None, len(headers) - 1)
        if len(parts) >= 2:
            rows.append(dict(zip(headers, parts)))
    return rows


# ---------- token classification --------------------------------------------

def classify_token(jwt_str: str) -> dict:
    out = {"is_jwt": False, "alg": None, "typ": None, "kid": None}
    if not jwt_str or jwt_str.count(".") < 2:
        return out
    parts = jwt_str.split(".")
    try:
        padded = parts[0] + "=" * (-len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
        out["is_jwt"] = True
        out["alg"] = header.get("alg")
        out["typ"] = header.get("typ")
        out["kid"] = header.get("kid")
    except Exception:
        pass
    return out


def partition_tokens(tokens: list) -> dict:
    access, id_tok, unknown = [], [], []
    for t in tokens:
        if not isinstance(t, str) or t.count(".") != 2:
            unknown.append(t)
            continue
        cls = classify_token(t)
        if not cls["is_jwt"]:
            unknown.append(t)
            continue
        try:
            payload_b64 = t.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            if "wids" in payload or payload.get("typ") == "ID":
                id_tok.append(t)
            else:
                access.append(t)
        except Exception:
            access.append(t)
    return {"access_tokens": access, "id_tokens": id_tok, "unknown": unknown}


# ---------- normalization helpers --------------------------------------------

def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub('', text)


def strip_progress_bars(text: str) -> str:
    out = []
    for line in text.splitlines():
        cleaned = line.split('\r')[-1]
        bars = sum(1 for c in cleaned if c in '█▓▒░║│─')
        if len(cleaned) > 20 and bars / max(len(cleaned), 1) > 0.3:
            continue
        if cleaned.strip().endswith(('it/s]', 's/it]', 'B/s]')):
            continue
        out.append(cleaned)
    return '\n'.join(out)


def normalize(result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    stdout = result.get("stdout", "")
    cleaned = strip_progress_bars(strip_ansi(stdout))
    parsed = parse_stdout(cleaned)
    if parsed["tokens"]:
        parsed["token_breakdown"] = partition_tokens(parsed["tokens"])
    result["parsed"] = parsed
    result["stdout_clean"] = cleaned
    return result


# ---------- errors / summary / version ---------------------------------------

def extract_errors(result: dict) -> list:
    errs = []
    if not isinstance(result, dict):
        return errs
    for stream in ("stderr", "stdout"):
        text = result.get(stream, "")
        if not text:
            continue
        for line in strip_ansi(text).splitlines():
            m = _ERROR_LINE.match(line)
            if m:
                errs.append({"stream": stream, "level": "error",
                             "message": m.group(1).strip()})
                continue
            m = _WARN_LINE.match(line)
            if m:
                errs.append({"stream": stream, "level": "warning",
                             "message": m.group(1).strip()})
                continue
            m = _HTTP_ERROR.search(line)
            if m:
                errs.append({"stream": stream, "level": "http",
                             "status": int(m.group(1)),
                             "message": m.group(2)})
    return errs


def build_summary(parsed: dict) -> dict:
    return {
        "line_count": len(parsed.get("lines", [])),
        "json_objects": len(parsed.get("json_objects", [])),
        "tokens": len(parsed.get("tokens", [])),
        "emails": len(parsed.get("emails", [])),
        "tenant_ids": len(parsed.get("tenant_ids", [])),
        "user_ids": len(parsed.get("user_ids", [])),
        "app_ids": len(parsed.get("app_ids", [])),
        "user_codes": len(parsed.get("user_codes", [])),
        "role_names": len(parsed.get("role_names", [])),
        "has_verification_url": parsed.get("verification_url") is not None,
    }


def extract_version(stdout: str) -> Optional[str]:
    if not stdout:
        return None
    m = _VERSION_LINE.search(stdout)
    return m.group(1) if m else None


def diff_entities(before: list, after: list, key: str = "id") -> dict:
    bm = {e.get(key): e for e in before if e.get(key)}
    am = {e.get(key): e for e in after if e.get(key)}
    added = [am[k] for k in am.keys() - bm.keys()]
    removed = [bm[k] for k in bm.keys() - am.keys()]
    common = bm.keys() & am.keys()
    modified = [{"before": bm[k], "after": am[k], "key": k}
                for k in common if bm[k] != am[k]]
    return {"added": added, "removed": removed, "modified": modified}


def dedupe_by(rows: list, key: str = "id") -> list:
    seen, out = set(), []
    for r in rows:
        k = r.get(key)
        if k and k not in seen:
            seen.add(k)
            out.append(r)
    return out


def build_gather_all_dump(parsed: dict) -> dict:
    return {
        "users": extract_users(parsed),
        "groups": extract_groups(parsed),
        "applications": extract_applications(parsed),
        "service_principals": extract_service_principals(parsed),
        "directory_roles": extract_directory_roles(parsed),
        "conditional_access_policies": extract_conditional_access_policies(parsed),
    }


# ---------- top-level dispatcher -------------------------------------------

def parse(activity: str, result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    parsed = result.get("parsed") or parse_stdout(
        result.get("stdout_clean", result.get("stdout", "")))
    if activity == "list-users":
        result["users"] = extract_users(parsed)
    elif activity == "list-applications":
        result["applications"] = extract_applications(parsed)
    elif activity == "list-interest":
        result["items"] = extract_interest(parsed)
    elif activity == "gather-all":
        result["dump"] = build_gather_all_dump(parsed)
    elif activity in ("self", "auth", "auth-app", "load", "refresh", "magic-app"):
        cap = extract_phish_capture(parsed)
        if cap["access_token"]:
            result["capture"] = cap
    elif activity == "phish-capture":
        result["capture"] = extract_phish_capture(parsed)
    elif activity in ("spray", "spray-refresh"):
        result["spray_result"] = parse_spray_result(parsed)
    elif activity == "knownids":
        result["known_ids"] = parse_known_ids_table(parsed)
    elif activity == "push-file":
        result["files"] = extract_files(parsed)
    elif activity in ("add-group", "add-roles"):
        if parsed.get("role_names"):
            result["roles"] = parsed["role_names"]
    if "errors" not in result:
        result["errors"] = extract_errors(result)
    result["summary"] = build_summary(parsed)
    return result