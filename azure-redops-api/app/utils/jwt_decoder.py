"""JWT decoder utility - decodes header + payload without verification."""
import base64
import json
import time


def _b64url_decode(s: str) -> bytes:
    s = s.strip() + "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())


def decode_jwt(token):
    """Decode a JWT (header + payload) without signature verification.

    Returns None on empty/non-string input, {} on malformed JWT,
    and a full dict on valid JWT.
    """
    if not token:
        return None
    if not isinstance(token, str):
        return None
    if token.count('.') < 2:
        return None
    parts = token.split('.')
    try:
        header = json.loads(_b64url_decode(parts[0]))
    except Exception:
        header = {}
    try:
        payload = json.loads(_b64url_decode(parts[1]))
    except Exception:
        payload = {}
    sig = parts[2] if len(parts) > 2 else ''
    is_expired = bool(payload.get('exp') and payload['exp'] < time.time())
    return {
        'header': header,
        'payload': payload,
        'signature_present': bool(sig),
        'is_expired': is_expired,
        'expires_at_iso': (
            __import__('datetime').datetime.fromtimestamp(
                payload['exp'], tz=__import__('datetime').timezone.utc
            ).isoformat()
            if payload.get('exp') else None
        ),
    }