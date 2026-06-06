from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import requests

from .paths import FLOAT_DIR, FLOAT_EXE_NAME, INSTALL_DIR, TRAY_EXE_NAME, UPDATES_DIR, iniciar_cmd_path
from .updater import UpdateInfo

INICIAR_CMD = """@echo off
REM Desbloquea archivos descargados de Internet (Mark of the Web) y abre la app.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-ChildItem -LiteralPath '%~dp0' -Recurse -File | ForEach-Object { Unblock-File -LiteralPath $_.FullName -ErrorAction SilentlyContinue }"
start "" "%~dp0cursor-usage-tray.exe"
"""


def _unblock_directory(path: Path) -> None:
    if not path.exists():
        return
    subprocess.run(  # noqa: S603
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                f"Get-ChildItem -LiteralPath '{path}' -Recurse -File | "
                "ForEach-Object { Unblock-File -LiteralPath $_.FullName -ErrorAction SilentlyContinue }"
            ),
        ],
        check=False,
        capture_output=True,
    )


def _download_release(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)


def _find_float_dir(extracted_root: Path) -> Path | None:
    candidates = [
        extracted_root / "float",
        extracted_root / "cursor-usage-tray" / "float",
        extracted_root,
    ]
    for candidate in candidates:
        if (candidate / FLOAT_EXE_NAME).exists():
            return candidate
    for path in extracted_root.rglob(FLOAT_EXE_NAME):
        return path.parent
    return None


def _replace_directory(source: Path, target: Path) -> None:
    backup = target.with_name(f"{target.name}.old")
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    if target.exists():
        target.rename(backup)
    shutil.copytree(source, target)
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)


def install_float_update(info: UpdateInfo) -> None:
    if not info.download_url:
        raise RuntimeError("La release no incluye un archivo zip para descargar.")

    zip_path = UPDATES_DIR / f"cursor-usage-tray-v{info.version}.zip"
    staging_root = UPDATES_DIR / "staging" / info.version
    extract_dir = staging_root / "extracted"

    if staging_root.exists():
        shutil.rmtree(staging_root, ignore_errors=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    _download_release(info.download_url, zip_path)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    float_source = _find_float_dir(extract_dir)
    if float_source is None:
        raise RuntimeError("No se encontró cursor-usage-float.exe en el zip descargado.")

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    tray_candidates = list(extract_dir.rglob(TRAY_EXE_NAME))
    if tray_candidates:
        tray_source_dir = tray_candidates[0].parent
        for name in (TRAY_EXE_NAME, "_internal", "Iniciar.cmd"):
            src = tray_source_dir / name
            if src.exists():
                dest = INSTALL_DIR / name
                if src.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)

    iniciar = iniciar_cmd_path()
    if not iniciar.exists():
        iniciar.write_text(INICIAR_CMD, encoding="utf-8")

    _replace_directory(float_source, FLOAT_DIR)
    _unblock_directory(FLOAT_DIR)
    _unblock_directory(INSTALL_DIR)

    shutil.rmtree(staging_root, ignore_errors=True)
