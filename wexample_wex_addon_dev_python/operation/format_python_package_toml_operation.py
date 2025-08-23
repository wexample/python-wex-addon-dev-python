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
        from tomlkit.items import Array, String

        if not isinstance(arr, Array):
            return False

        items = list(arr)
        if not items or not all(isinstance(i, String) for i in items):
            return False

        values = [i.value for i in items]
        # Compute sorted order using existing String items to preserve style/quotes/comments
        sorted_items = [
            x
            for _, x in sorted(
                zip([v.lower() for v in values], items), key=lambda t: t[0]
            )
        ]

        if items == sorted_items:
            return False

        # Rebuild in place with the original items, preserving style/quotes/comments and multiline flag
        multiline_flag = getattr(arr, "multiline", None)
        while len(arr):
            arr.pop()
        for item in sorted_items:
            arr.append(item)
        if multiline_flag is not None:
            arr.multiline(multiline_flag)

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

        package_workdir = target.find_package_workdir()
        if package_workdir is not None:
            version = package_workdir.get_version()

            project_tbl = doc.get("project") if isinstance(doc, dict) else None
            if project_tbl and isinstance(project_tbl, dict):
                current_version = project_tbl.get("version")
                if current_version != version:
                    project_tbl["version"] = version
                    changed = True

        # Handle [project].dependencies
        project_tbl = doc.get("project") if isinstance(doc, dict) else None
        if project_tbl and isinstance(project_tbl, dict):
            # Enforce minimum Python version
            target_requires = ">=3.12"
            current_requires = project_tbl.get("requires-python")
            if current_requires != target_requires:
                project_tbl["requires-python"] = target_requires
                changed = True
            deps = project_tbl.get("dependencies")
            if deps is not None:
                changed |= cls._sort_array_of_strings(deps)

            # Also handle [project.optional-dependencies]
            opt_deps = project_tbl.get("optional-dependencies")
            if opt_deps and isinstance(opt_deps, dict):
                for _group, arr in opt_deps.items():
                    changed |= cls._sort_array_of_strings(arr)

            # Enforce rule: remove pytest from runtime deps, ensure it exists in optional deps (dev)
            # 1) Remove any pytest entry from [project].dependencies
            if deps is not None:
                from tomlkit.items import String

                def _is_pytest_string(item: object) -> bool:
                    if isinstance(item, String):
                        v = item.value.strip()
                        return v == "pytest"
                    return False

                len(list(deps))
                # Collect indices to remove to avoid modifying while iterating
                to_remove = [
                    idx for idx, it in enumerate(list(deps)) if _is_pytest_string(it)
                ]
                for idx in reversed(to_remove):
                    deps.pop(idx)
                if to_remove:
                    changed = True
                    # Re-sort after modification
                    changed |= cls._sort_array_of_strings(deps)

            # 2) Ensure [project.optional-dependencies].dev exists and contains pytest
            if not opt_deps or not isinstance(opt_deps, dict):
                # Create the table if missing
                from tomlkit import array, table

                opt_deps = table()
                project_tbl["optional-dependencies"] = opt_deps
                changed = True

            # Ensure "dev" group exists
            dev_arr = opt_deps.get("dev")
            if dev_arr is None:
                from tomlkit import array

                dev_arr = array()
                # Make it a nice inline or multiline array depending on style; default inline
                opt_deps["dev"] = dev_arr
                changed = True

            # Add pytest if missing
            from tomlkit.items import String

            values = [
                it.value if isinstance(it, String) else str(it) for it in list(dev_arr)
            ]
            if not any(
                v == "pytest"
                or v.startswith("pytest ")
                or v.startswith("pytest>=")
                or v.startswith("pytest==")
                or v.startswith("pytest<")
                for v in values
            ):
                dev_arr.append("pytest")
                changed = True
                changed |= cls._sort_array_of_strings(dev_arr)

        # If no change occurred, signal no-op to avoid churn
        if not changed:
            return None

        # Dump back; tomlkit preserves formatting/comments
        updated = tomlkit.dumps(doc)
        return updated

    def applicable_for_option(self, option: AbstractConfigOption) -> bool:
        from wexample_wex_addon_dev_python.config_option.format_python_package_toml_option import (
            FormatPythonPackageTomlOption,
        )

        if not isinstance(option, FormatPythonPackageTomlOption):
            return False

        return self.source_need_change(self.target)

    def describe_before(self) -> str:
        return "The pyproject.toml file is not normalized/formatted."

    def describe_after(self) -> str:
        return "The pyproject.toml file has been normalized/formatted."

    def description(self) -> str:
        return "Format the pyproject.toml file of a Python package using tomlkit."
