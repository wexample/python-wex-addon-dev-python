from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.operation.abstract_existing_file_operation import (
    AbstractExistingFileOperation,
)

if TYPE_CHECKING:
    from wexample_config.config_option.abstract_config_option import (
        AbstractConfigOption,
    )
    from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType


class FormatPythonPackageTomlOperation(AbstractExistingFileOperation):
    """Format a Python package's pyproject.toml using tomlkit.

    Triggered by: { "format_python_package_toml": true }
    """

    @classmethod
    def get_option_name(cls) -> str:
        from wexample_wex_addon_dev_python.config_option.format_python_package_toml_option import (
            FormatPythonPackageTomlOption,
        )

        return FormatPythonPackageTomlOption.OPTION_NAME

    @classmethod
    def _sort_array_of_strings(cls, arr) -> bool:
        """Sort a tomlkit Array of strings in place.

        Assumes the array exists and contains only string items.
        Returns True if a re-ordering was applied, False otherwise.
        """
        from tomlkit import array, string
        from tomlkit.items import Array, String

        if not isinstance(arr, Array):
            return False

        items = list(arr)
        if not items or not all(isinstance(i, String) for i in items):
            return False

        values = [i.value for i in items]
        sorted_values = sorted(values, key=lambda s: s.lower())
        if values == sorted_values:
            return False

        # rebuild preserving multiline style
        new_arr = array([string(v) for v in sorted_values])
        new_arr.multiline(arr.multiline)

        while len(arr):
            arr.pop()
        for item in new_arr:
            arr.append(item)

        return True

    @classmethod
    def preview_source_change(cls, target: TargetFileOrDirectoryType) -> str | None:
        import tomlkit

        src = cls._read_current_non_empty_src(target)
        # If no meaningful content, no change is proposed
        if src is None:
            return None

        doc = tomlkit.parse(src)

        changed = False

        # Handle [project].dependencies
        project_tbl = doc.get("project") if isinstance(doc, dict) else None
        if project_tbl and isinstance(project_tbl, dict):
            deps = project_tbl.get("dependencies")
            if deps is not None:
                changed |= cls._sort_array_of_strings(deps)

            # Also handle [project.optional-dependencies]
            opt_deps = project_tbl.get("optional-dependencies")
            if opt_deps and isinstance(opt_deps, dict):
                for _group, arr in opt_deps.items():
                    changed |= cls._sort_array_of_strings(arr)

        # If no change occurred, signal no-op to avoid churn
        if not changed:
            return None

        # Dump back; tomlkit preserves formatting/comments
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

        return cls.source_need_change(target)

    def describe_before(self) -> str:
        return "The pyproject.toml file is not normalized/formatted."

    def describe_after(self) -> str:
        return "The pyproject.toml file has been normalized/formatted."

    def description(self) -> str:
        return "Format the pyproject.toml file of a Python package using tomlkit."
