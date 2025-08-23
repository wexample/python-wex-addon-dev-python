from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.operations_provider.abstract_operations_provider import (
    AbstractOperationsProvider,
)

if TYPE_CHECKING:
    from wexample_filestate.operation.abstract_operation import AbstractOperation


class DevPythonOperationsProvider(AbstractOperationsProvider):
    @staticmethod
    def get_operations() -> list[type[AbstractOperation]]:
        from wexample_wex_addon_dev_python.operation.format_python_package_toml_operation import (
            FormatPythonPackageTomlOperation,
        )

        return [FormatPythonPackageTomlOperation]
