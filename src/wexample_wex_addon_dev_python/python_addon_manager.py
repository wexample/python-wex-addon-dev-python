from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_wex_core.common.abstract_addon_manager import AbstractAddonManager

if TYPE_CHECKING:
    from wexample_cli.middleware.abstract_middleware import AbstractMiddleware


class PythonAddonManager(AbstractAddonManager):
    def get_local_configurable_keys(self) -> list[dict]:
        from wexample_wex_addon_dev_python.helpers.pdm import (
            apply_pdm_bin_dir,
            detect_pdm_bin_dir,
        )

        return [
            {
                "key": "PDM_BIN_DIR",
                "description": "Directory containing pdm — required to publish Python packages",
                "detect": detect_pdm_bin_dir,
                "on_apply": apply_pdm_bin_dir,
            }
        ]

    def get_middlewares_classes(self) -> list[type[AbstractMiddleware]]:
        from wexample_wex_addon_dev_python.middleware.each_python_file_middleware import (
            EachPythonFileMiddleware,
        )

        return [
            EachPythonFileMiddleware,
        ]
