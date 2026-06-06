from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import APP_DIR
from .__version__ import GITHUB_REPO, __version__

LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
UPDATE_STATE_PATH = APP_DIR / "update_state.json"


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    page_url: str
    download_url: str | None


def parse_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lstrip("vV").split("-", 1)[0]
    parts: list[int] = []
    for piece in cleaned.split("."):
        if not piece.isdigit():
            break
        parts.append(int(piece))
    return tuple(parts) if parts else (0,)


def is_newer(latest: str, current: str = __version__) -> bool:
    return parse_version(latest) > parse_version(current)


def _load_state() -> dict:
    if not UPDATE_STATE_PATH.exists():
        return {}
    try:
        return json.loads(UPDATE_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def is_dismissed(version: str) -> bool:
    return _load_state().get("dismissed_version") == version


def dismiss_version(version: str) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    UPDATE_STATE_PATH.write_text(
        json.dumps({"dismissed_version": version}, indent=2),
        encoding="utf-8",
    )


def fetch_latest_release(timeout: float = 12.0) -> UpdateInfo | None:
    response = requests.get(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    version = str(data.get("tag_name", "")).lstrip("vV")
    if not version:
        return None

    page_url = str(data.get("html_url") or RELEASES_PAGE)
    download_url: str | None = None
    for asset in data.get("assets") or []:
        name = str(asset.get("name", "")).lower()
        if name.endswith(".zip") or name.endswith(".exe"):
            download_url = str(asset.get("browser_download_url") or "") or None
            break

    return UpdateInfo(version=version, page_url=page_url, download_url=download_url)
