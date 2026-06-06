from __future__ import annotations

import base64
import json
import os
import sqlite3
from pathlib import Path
from typing import Optional


def _cursor_state_db_paths() -> list[Path]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []
    roots = (
        Path(appdata) / "Cursor",
        Path(appdata) / "cursor",
    )
    return [
        root / "User" / "globalStorage" / "state.vscdb"
        for root in roots
        if (root / "User" / "globalStorage" / "state.vscdb").exists()
    ]


def _normalize_stored_value(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        try:
            decoded = json.loads(text)
            if isinstance(decoded, str):
                return decoded.strip()
        except json.JSONDecodeError:
            pass
    return text


def _read_item(key: str) -> Optional[str]:
    for db_path in _cursor_state_db_paths():
        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                row = conn.execute("SELECT value FROM ItemTable WHERE key = ?", (key,)).fetchone()
                if row and row[0]:
                    return _normalize_stored_value(str(row[0]))
        except sqlite3.Error:
            continue
    return None


def _user_id_from_jwt(access_token: str) -> Optional[str]:
    try:
        payload_b64 = access_token.split(".")[1]
        padding = "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
        sub = str(payload.get("sub", ""))
        if "|" in sub:
            return sub.split("|", 1)[1]
        return sub or None
    except (IndexError, json.JSONDecodeError, ValueError):
        return None


def build_session_token_from_access_token(access_token: str) -> Optional[str]:
    user_id = _user_id_from_jwt(access_token)
    if not user_id:
        return None
    return f"{user_id}%3A%3A{access_token}"


def resolve_cursor_account_email() -> Optional[str]:
    email = _read_item("cursorAuth/cachedEmail")
    return email.strip() if email else None


def resolve_session_token() -> tuple[Optional[str], str]:
    """Read the current user's Cursor session from local storage (never from config/code)."""
    db_paths = _cursor_state_db_paths()
    if not db_paths:
        return None, "Cursor no encontrado (%APPDATA%\\Cursor\\User\\globalStorage\\state.vscdb)"

    for key in (
        "cursorAuth/WorkosCursorSessionToken",
        "WorkosCursorSessionToken",
        "cursorAuth/sessionToken",
    ):
        value = _read_item(key)
        if value:
            return value, f"Cursor local ({key})"

    access_token = _read_item("cursorAuth/accessToken")
    if access_token:
        built = build_session_token_from_access_token(access_token)
        if built:
            return built, "Cursor local (cursorAuth/accessToken)"

    return None, "Sin sesión en Cursor. Abrí Cursor e iniciá sesión en tu cuenta."
