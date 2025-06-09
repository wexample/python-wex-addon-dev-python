from typing import List, Type

from wexample_wex_core.common.abstract_addon_manager import AbstractAddonManager
from wexample_wex_core.middleware.abstract_middleware import AbstractMiddleware


class PythonAddonManager(AbstractAddonManager):
    def get_middlewares_classes(self) -> List[Type["AbstractMiddleware"]]:
        from wexample_wex_addon_dev_python.middleware.each_python_file_middleware import EachPythonFileMiddleware

        return [
            EachPythonFileMiddleware,
        ]
