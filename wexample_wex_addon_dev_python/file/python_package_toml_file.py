from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_config.const.types import DictConfig
from wexample_filestate.item.file.toml_file import TomlFile

if TYPE_CHECKING:
    from wexample_wex_addon_dev_python.workdir.python_packages_suite_workdir import (
        PythonPackagesSuiteWorkdir,
    )


class PythonPackageTomlFile(TomlFile):
    def prepare_value(self, prepare_value: DictConfig | None = None) -> DictConfig:
        from wexample_wex_addon_dev_python.config_option.format_python_package_toml_option import (
            FormatPythonPackageTomlOption,
        )

        prepare_value[FormatPythonPackageTomlOption.get_snake_short_class_name()] = True

        return prepare_value

    def find_package_workdir(self) -> PythonPackagesSuiteWorkdir | None:
        from wexample_wex_addon_dev_python.workdir.python_package_workdir import (
            PythonPackageWorkdir,
        )

        return self.find_closest(PythonPackageWorkdir)

    def find_suite_workdir(self) -> PythonPackagesSuiteWorkdir | None:
        from wexample_wex_addon_dev_python.workdir.python_packages_suite_workdir import (
            PythonPackagesSuiteWorkdir,
        )

        return self.find_closest(PythonPackagesSuiteWorkdir)

    @classmethod
    def _sort_array_of_strings(cls, arr) -> bool:
        """Sort a tomlkit Array of String items in-place (case-insensitive) preserving style."""
        from tomlkit.items import Array, String

        if not isinstance(arr, Array):
            return False

        items = list(arr)
        if not items or not all(isinstance(i, String) for i in items):
            return False

        values = [i.value for i in items]
        sorted_items = [x for _, x in sorted(zip([v.lower() for v in values], items), key=lambda t: t[0])]

        if items == sorted_items:
            return False

        multiline_flag = getattr(arr, "multiline", None)
        while len(arr):
            arr.pop()
        for item in sorted_items:
            arr.append(item)
        if multiline_flag is not None:
            arr.multiline(multiline_flag)
        return True

    @classmethod
    def format_toml_doc(cls, target: PythonPackageTomlFile, doc) -> bool:
        """Apply formatting/rules to a parsed tomlkit doc. Returns True if changed."""
        changed = False

        # Sync version from package workdir if available
        package_workdir = target.find_package_workdir()
        if package_workdir is not None:
            version = package_workdir.get_version()
            project_tbl = doc.get("project") if isinstance(doc, dict) else None
            if project_tbl and isinstance(project_tbl, dict):
                current_version = project_tbl.get("version")
                if current_version != version:
                    project_tbl["version"] = version
                    changed = True

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

            # Sort optional deps arrays
            opt_deps = project_tbl.get("optional-dependencies")
            if opt_deps and isinstance(opt_deps, dict):
                for _group, arr in opt_deps.items():
                    changed |= cls._sort_array_of_strings(arr)

            # Remove pytest from runtime deps
            if deps is not None:
                from tomlkit.items import String

                def _is_pytest_string(item: object) -> bool:
                    if isinstance(item, String):
                        v = item.value.strip()
                        return v == "pytest"
                    return False

                to_remove = [idx for idx, it in enumerate(list(deps)) if _is_pytest_string(it)]
                for idx in reversed(to_remove):
                    deps.pop(idx)
                if to_remove:
                    changed = True
                    changed |= cls._sort_array_of_strings(deps)

            # Ensure dev optional-dependencies has pytest
            if not opt_deps or not isinstance(opt_deps, dict):
                from tomlkit import table

                opt_deps = table()
                project_tbl["optional-dependencies"] = opt_deps
                changed = True

            dev_arr = opt_deps.get("dev")
            if dev_arr is None:
                from tomlkit import array

                dev_arr = array()
                opt_deps["dev"] = dev_arr
                changed = True

            from tomlkit.items import String
            values = [it.value if isinstance(it, String) else str(it) for it in list(dev_arr)]
            if not any(
                v == "pytest"
                for v in values
            ):
                dev_arr.append("pytest")
                changed = True
                changed |= cls._sort_array_of_strings(dev_arr)

        return changed

    @classmethod
    def apply_format_to_src(cls, target: PythonPackageTomlFile, src: str) -> str | None:
        """Parse, format, and dump toml; return updated string or None if no changes."""
        import tomlkit

        doc = tomlkit.parse(src)
        changed = cls.format_toml_doc(target, doc)
        if not changed:
            return None
        return tomlkit.dumps(doc)
