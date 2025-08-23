from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.enum.scopes import Scope
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.operation.mixin.file_manipulation_operation_mixin import (
    FileManipulationOperationMixin,
)

if TYPE_CHECKING:
    from wexample_config.config_option.abstract_config_option import (
        AbstractConfigOption,
    )
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class FormatPythonPackageTomlOperation(
    FileManipulationOperationMixin, AbstractOperation
):
    """Format a Python package's pyproject.toml using tomlkit.

    Triggered by: { "format_python_package_toml": true }
    """

    @classmethod
    def get_scope(cls) -> Scope:
        return Scope.CONTENT

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_wex_addon_dev_python.config_option.format_python_package_toml_option import (
            FormatPythonPackageTomlOption,
        )

        return FormatPythonPackageTomlOption.OPTION_NAME

    @classmethod
    def preview_source_change(cls, src: str) -> str:
        import tomlkit

        doc = tomlkit.parse(src)
        # Round-trip dump; tomlkit preserves comments/formatting while normalizing structure
        updated = tomlkit.dumps(doc)
        return updated

    @classmethod
    def applicable_option(
            cls, target: TargetFileOrDirectoryType, option: AbstractConfigOption
    ) -> bool:
        from wexample_wex_addon_dev_python.config_option.format_python_package_toml_option import (
            FormatPythonPackageTomlOption,
        )

        if not isinstance(option, FormatPythonPackageTomlOption):
            return False

        local = target.get_local_file()
        if not (target.is_file() and local.path.exists()):
            return False

        src = target.get_local_file().read()
        if src.strip() == "":
            return False

        updated = cls.preview_source_change(src)
        return updated != src

    def describe_before(self) -> str:
        return "The pyproject.toml file is not normalized/formatted."

    def describe_after(self) -> str:
        return "The pyproject.toml file has been normalized/formatted."

    def description(self) -> str:
        return "Format the pyproject.toml file of a Python package using tomlkit."

    def apply(self) -> None:
        src = self.target.get_local_file().read()
        updated = self.preview_source_change(src)
        if updated != src:
            self._target_file_write(content=updated)
