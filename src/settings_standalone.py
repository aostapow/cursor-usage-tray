from __future__ import annotations

from .config import AppConfig
from .ipc_signals import request_label_reset
from .settings import open_settings_dialog


def run_settings_dialog() -> None:
    config = AppConfig.load()

    def on_save(_updated: AppConfig) -> None:
        pass

    def on_reset_label_position() -> None:
        request_label_reset()

    def get_label_position() -> tuple[int | None, int | None]:
        current = AppConfig.load()
        return current.label_x, current.label_y

    open_settings_dialog(
        config,
        on_save,
        on_reset_label_position=on_reset_label_position,
        on_get_label_position=get_label_position,
    )
