"""IMAP mailbox proxy endpoints. Reads sessions from token_store."""
from __future__ import annotations

import imaplib
import email
from email.header import make_header, decode_header

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.utils import token_store

router = APIRouter(prefix="/mailbox", tags=["IMAP Mailbox Proxy"])


class MbxIn(BaseModel):
    name: str
    email: str
    imap_host: str
    imap_port: int = 993
    password: str
    use_ssl: bool = True


class ForwardIn(BaseModel):
    to: str
    msg_id: str
    folder: str = "INBOX"


def _decode(h):
    if not h:
        return ""
    try:
        return str(make_header(decode_header(h)))
    except Exception:
        return h


def _connect(s):
    if s["use_ssl"]:
        c = imaplib.IMAP4_SSL(s["imap_host"], s["imap_port"])
    else:
        c = imaplib.IMAP4(s["imap_host"], s["imap_port"])
    c.login(s["email"], s["password"])
    return c


def _parse(raw):
    msg = email.message_from_bytes(raw)
    body = ""
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and not p.get("Content-Disposition"):
                body = p.get_payload(decode=True).decode("utf-8", "ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode("utf-8", "ignore")
    return {
        "subject": _decode(msg.get("Subject")),
        "from": _decode(msg.get("From")),
        "to": _decode(msg.get("To")),
        "date": msg.get("Date"),
        "body": body[:8000],
        "message_id": msg.get("Message-ID", ""),
    }


@router.post("/sessions")
def add_session(s: MbxIn):
    return token_store.save_mailbox_session(
        s.name, s.email, s.imap_host, s.imap_port, s.password, int(s.use_ssl)
    )


@router.get("/sessions")
def list_sessions():
    return {"sessions": token_store.list_mailbox_sessions()}


@router.delete("/sessions/{name}")
def remove_session(name: str):
    return token_store.delete_mailbox_session(name)


@router.get("/proxy/{name}/folders")
def folders(name: str):
    s = token_store.get_mailbox_session(name)
    if not s:
        raise HTTPException(404, "session not found")
    c = _connect(s)
    try:
        _, data = c.list()
        folders = []
        for raw in (data or []):
            parts = raw.decode().split(' "/" ')
            if len(parts) >= 2:
                folders.append(parts[-1].strip('"'))
        return {"folders": folders}
    finally:
        try:
            c.logout()
        except Exception:
            pass


@router.get("/proxy/{name}/messages")
def messages(name: str, folder: str = "INBOX", limit: int = 25, offset: int = 0):
    s = token_store.get_mailbox_session(name)
    if not s:
        raise HTTPException(404, "session not found")
    c = _connect(s)
    try:
        c.select(folder)
        _, data = c.search(None, "ALL")
        ids = data[0].split()[::-1][offset:offset + limit]
        out = []
        for mid in ids:
            _, md = c.fetch(mid, "(RFC822)")
            out.append({"id": mid.decode(), **_parse(md[0][1])})
        return {"messages": out, "folder": folder}
    finally:
        try:
            c.logout()
        except Exception:
            pass


@router.get("/proxy/{name}/message/{msg_id}")
def message(name: str, msg_id: str, folder: str = "INBOX"):
    s = token_store.get_mailbox_session(name)
    if not s:
        raise HTTPException(404, "session not found")
    c = _connect(s)
    try:
        c.select(folder)
        _, md = c.fetch(msg_id, "(RFC822)")
        return _parse(md[0][1])
    finally:
        try:
            c.logout()
        except Exception:
            pass


@router.post("/proxy/{name}/delete/{msg_id}")
def delete_msg(name: str, msg_id: str, folder: str = "INBOX"):
    s = token_store.get_mailbox_session(name)
    if not s:
        raise HTTPException(404, "session not found")
    c = _connect(s)
    try:
        c.select(folder)
        c.store(msg_id, "+FLAGS", r"\Deleted")
        c.expunge()
        return {"ok": True}
    finally:
        try:
            c.logout()
        except Exception:
            pass


@router.post("/proxy/{name}/flag/{msg_id}/{flag}")
def flag_msg(name: str, msg_id: str, flag: str, folder: str = "INBOX", value: bool = True):
    s = token_store.get_mailbox_session(name)
    if not s:
        raise HTTPException(404, "session not found")
    c = _connect(s)
    try:
        c.select(folder)
        c.store(msg_id, "+FLAGS" if value else "-FLAGS", flag)
        return {"ok": True}
    finally:
        try:
            c.logout()
        except Exception:
            pass


@router.post("/proxy/{name}/forward")
def forward(name: str, req: ForwardIn):
    s = token_store.get_mailbox_session(name)
    if not s:
        raise HTTPException(404, "session not found")
    return {
        "ok": True,
        "to": req.to,
        "msg_id": req.msg_id,
        "note": "Wire to smtplib relay (out of scope for proxy)",
    }