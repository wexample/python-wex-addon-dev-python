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

    def format_toml_doc(self, doc) -> bool:
        from wexample_filestate_python.helpers.toml import (
            toml_ensure_array,
            toml_ensure_table,
            toml_get_string_value,
            toml_sort_string_array,
        )
        from wexample_helpers.helpers.string import string_to_snake_case

        """Apply formatting/rules to a parsed tomlkit doc. Returns True if changed."""
        changed = False

        # Sync version from package workdir if available
        package_workdir = self.find_package_workdir()

        project_name = package_workdir.get_project_name()
        # Heuristic import name: distribution name converted to snake_case
        import_name = string_to_snake_case(project_name) if isinstance(project_name, str) else None

        if package_workdir is not None:
            version = package_workdir.get_project_version()
            project_tbl = doc.get("project") if isinstance(doc, dict) else None
            if project_tbl and isinstance(project_tbl, dict):
                current_version = project_tbl.get("version")
                if current_version != version:
                    project_tbl["version"] = version
                    changed = True

        # Ensure modern build backend: pdm-backend
        from tomlkit import table

        build_tbl = doc.get("build-system") if isinstance(doc, dict) else None
        if not build_tbl or not isinstance(build_tbl, dict):
            build_tbl = table()
            doc["build-system"] = build_tbl
            changed = True
        # Always enforce pdm-backend
        requires_list = build_tbl.get("requires")
        desired_requires = ["pdm-backend"]
        if requires_list != desired_requires:
            build_tbl["requires"] = desired_requires
            changed = True
        if build_tbl.get("build-backend") != "pdm.backend":
            build_tbl["build-backend"] = "pdm.backend"
            changed = True

        # Ensure [tool.pdm.build] includes py.typed (and package itself if include list is used)
        tool_tbl, ch1 = toml_ensure_table(doc, ["tool"])
        pdm_tbl, ch2 = toml_ensure_table(tool_tbl, ["pdm"])
        build_pdm_tbl, ch3 = toml_ensure_table(pdm_tbl, ["build"])
        includes_arr, ch4 = toml_ensure_array(build_pdm_tbl, "includes")
        if ch1 or ch2 or ch3 or ch4:
            changed = True
        # Enforce src layout for packaging
        if import_name:
            # Ensure package-dir = "src"
            if build_pdm_tbl.get("package-dir") != "src":
                build_pdm_tbl["package-dir"] = "src"
                changed = True

            # Ensure packages = [{ include = import_name, from = "src" }]
            try:
                from tomlkit import inline_table  # type: ignore
            except Exception:  # pragma: no cover - very defensive
                inline_table = None

            desired_pkg = {"include": import_name, "from": "src"}
            current_pkgs = build_pdm_tbl.get("packages")
            need_set_pkgs = True
            if isinstance(current_pkgs, list) and len(current_pkgs) == 1:
                it = current_pkgs[0]
                # Compare as plain dict
                try:
                    it_as_dict = {k: str(v) for k, v in it.items()}  # type: ignore[attr-defined]
                except Exception:
                    it_as_dict = None
                if it_as_dict == {"include": import_name, "from": "src"}:
                    need_set_pkgs = False

            if need_set_pkgs and inline_table is not None:
                it = inline_table()
                it.update(desired_pkg)
                build_pdm_tbl["packages"] = [it]
                changed = True

        # Ensure py.typed is included for typing completeness
        if import_name:
            desired_includes = {f"src/{import_name}/py.typed"}
            current_includes = {str(x) for x in list(includes_arr)}
            missing = desired_includes - current_includes
            if missing:
                for item in sorted(missing):
                    includes_arr.append(item)
                changed = True

        project_tbl = doc.get("project") if isinstance(doc, dict) else None
        if project_tbl and isinstance(project_tbl, dict):
            # Enforce minimum Python version
            target_requires = ">=3.10"
            current_requires = project_tbl.get("requires-python")
            if current_requires != target_requires:
                project_tbl["requires-python"] = target_requires
                changed = True

            deps = project_tbl.get("dependencies")
            if deps is not None:
                changed |= toml_sort_string_array(deps)

            # Sort optional deps arrays
            opt_deps = project_tbl.get("optional-dependencies")
            if opt_deps and isinstance(opt_deps, dict):
                for _group, arr in opt_deps.items():
                    changed |= toml_sort_string_array(arr)

            # Inline comment protection disabled; use [tool.filestate].keep instead
            def _is_protected(item: object) -> bool:  # noqa: ARG001
                return False

            # Remove unwanted dev/build tools from runtime deps (unless explicitly protected)
            if deps is not None:
                import re as _re

                from tomlkit.items import String

                _REMOVE_NAMES = {
                    "pytest",
                    "pip-tools",
                    "black",
                    "ruff",
                    "flake8",
                    "mypy",
                    "isort",
                    "coverage",
                    "build",
                    "twine",
                    "pip",
                    "setuptools",
                    "wheel",
                    "typing-extensions",
                }

                def _norm_name(val: str) -> str:
                    # strip extras, versions, markers
                    base = _re.split(r"[\s<>=!~;\[]", val, maxsplit=1)[0]
                    return base.strip().lower()

                # Optional whitelist: [tool.filestate].keep = ["black", "isort", ...]
                keep_names: set[str] = set()
                if tool_tbl and isinstance(tool_tbl, dict):
                    filestate_tbl = tool_tbl.get("filestate")
                    if filestate_tbl and isinstance(filestate_tbl, dict):
                        keep_list = filestate_tbl.get("keep")
                        if isinstance(keep_list, list):
                            keep_names = {_norm_name(str(x)) for x in keep_list}

                def _should_remove(item: object) -> bool:
                    name = _norm_name(toml_get_string_value(item))
                    if name in keep_names:
                        return False
                    if name == "typing-extensions":
                        # requires-python is set to >=3.12 above -> safe to drop
                        return True
                    return name in _REMOVE_NAMES

                to_remove = [
                    idx
                    for idx, it in enumerate(list(deps))
                    if _should_remove(it) and not _is_protected(it)
                ]
                for idx in reversed(to_remove):
                    deps.pop(idx)
                if to_remove:
                    changed = True
                    changed |= toml_sort_string_array(deps)

                # Normalize any existing pydantic spec to pydantic>=2,<3
                normalized = False
                for i, it in enumerate(list(deps)):
                    val = toml_get_string_value(it).strip()
                    base = _norm_name(val)
                    if base == "pydantic" and not _is_protected(it):
                        if isinstance(it, String):
                            deps[i] = "pydantic>=2,<3"
                        else:
                            deps.pop(i)
                            deps.insert(i, "pydantic>=2,<3")
                        normalized = True
                if normalized:
                    changed = True
                    changed |= toml_sort_string_array(deps)

                # Ensure pydantic>=2,<3 is present unless excluded
                # Read optional exclusion list from [tool.filestate].exclude-add
                filestate_tbl = None
                exclude_add: set[str] = set()
                if tool_tbl and isinstance(tool_tbl, dict):
                    filestate_tbl = tool_tbl.get("filestate")
                if filestate_tbl and isinstance(filestate_tbl, dict):
                    ex = filestate_tbl.get("exclude-add")
                    if isinstance(ex, list):
                        exclude_add = {str(x).strip().lower() for x in ex}

                existing_names = {toml_get_string_value(it) for it in list(deps)}
                existing_norm = {_norm_name(v) for v in existing_names}
                if "pydantic" not in exclude_add and "pydantic" not in existing_norm:
                    deps.append("pydantic>=2,<3")
                    changed = True
                    changed |= toml_sort_string_array(deps)

            # Ensure dev optional-dependencies has pytest
            if not opt_deps or not isinstance(opt_deps, dict):
                from tomlkit import table

                opt_deps = table()
                project_tbl["optional-dependencies"] = opt_deps
                changed = True

            dev_arr = opt_deps.get("dev")
            if dev_arr is None:
                from tomlkit import array as _array

                dev_arr = _array()
                opt_deps["dev"] = dev_arr
                changed = True

            from tomlkit.items import String

            values = [toml_get_string_value(it) for it in list(dev_arr)]

            # Also avoid adding to dev if pytest already present in runtime deps
            has_runtime_pytest = False
            if deps is not None:
                has_runtime_pytest = any(
                    toml_get_string_value(it).strip() == "pytest"
                    for it in list(deps)
                )

            if not any(v == "pytest" for v in values) and not has_runtime_pytest:
                dev_arr.append("pytest")
                changed = True
                changed |= toml_sort_string_array(dev_arr)

        return changed

    def apply_format_to_src(self, src: str) -> str | None:
        """Parse, format, and dump toml; return updated string or None if no changes."""
        import tomlkit

        doc = tomlkit.parse(src)
        changed = self.format_toml_doc(doc)
        if not changed:
            return None
        return tomlkit.dumps(doc)
