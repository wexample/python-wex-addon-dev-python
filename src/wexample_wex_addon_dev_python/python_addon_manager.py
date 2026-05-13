from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_wex_core.common.abstract_addon_manager import AbstractAddonManager

if TYPE_CHECKING:
    from wexample_wex_core.middleware.abstract_middleware import AbstractMiddleware


def _detect_pdm_bin_dir() -> str | None:
    import pathlib
    import shutil

    if shutil.which("pdm"):
        return None
    local_bin = pathlib.Path.home() / ".local" / "bin"
    if (local_bin / "pdm").is_file():
        return str(local_bin)
    return None


def _apply_pdm_bin_dir(value: str) -> None:
    import os

    if value not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{value}:{os.environ.get('PATH', '')}"


class PythonAddonManager(AbstractAddonManager):
    def get_local_configurable_keys(self) -> list[dict]:
        return [
            {
                "key": "PDM_BIN_DIR",
                "description": "Directory containing pdm — required to publish Python packages",
                "detect": _detect_pdm_bin_dir,
                "on_apply": _apply_pdm_bin_dir,
            }
        ]

    def get_middlewares_classes(self) -> list[type[AbstractMiddleware]]:
        from wexample_wex_addon_dev_python.middleware.each_python_file_middleware import (
            EachPythonFileMiddleware,
        )

        return [
            EachPythonFileMiddleware,
        ]
