from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_wex_core.common.abstract_addon_manager import AbstractAddonManager

if TYPE_CHECKING:
    from wexample_wex_core.middleware.abstract_middleware import AbstractMiddleware


class PythonAddonManager(AbstractAddonManager):
    def get_middlewares_classes(self) -> list[type[AbstractMiddleware]]:
        from wexample_wex_addon_dev_python.middleware.each_python_file_middleware import (
            EachPythonFileMiddleware,
        )

        return [
            EachPythonFileMiddleware,
        ]
