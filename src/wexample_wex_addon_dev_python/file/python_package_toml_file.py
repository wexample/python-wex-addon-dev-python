from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.item.file.toml_file import TomlFile
from wexample_helpers.decorator.base_class import base_class
from wexample_wex_core.workdir.mixin.as_suite_package_item import (
    AsSuitePackageItem,
)

if TYPE_CHECKING:
    from tomlkit import TOMLDocument
    from wexample_wex_core.workdir.code_base_workdir import (
        CodeBaseWorkdir,
    )


@base_class
class PythonPackageTomlFile(AsSuitePackageItem, TomlFile):
    def add_dependency(
        self, spec: str, optional: bool = False, group: str = "dev"
    ) -> bool:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
        from wexample_filestate_python.helpers.toml import toml_sort_string_array

        deps = self._get_deps_array(optional=optional, group=group)
        # Remove existing entries for the same package name before adding the new spec.
        new_name = canonicalize_name(Requirement(spec).name)
        removed = self.remove_dependency_by_name(
            new_name, optional=optional, group=group
        )

        # Append (or re-append) the new spec if it is not already present verbatim
        if spec not in deps:
            deps.append(spec)
            toml_sort_string_array(deps)
            return True

        return removed

    def dumps(self, content: TOMLDocument | dict | None = None) -> str:
        """Serialize a TOMLDocument (preferred) or a plain dict to TOML.
        Using tomlkit.dumps preserves comments/formatting when content is a TOMLDocument.
        """
        from tomlkit import dumps
        content = content or self.read_parsed()

        package = self.find_package_workdir()
        import_name = package.get_package_import_name() if package else None
        project_name = package.get_package_name() if package else None
        project_version = package.get_project_version() if package else None

        self._enforce_build_system(content)
        self._enforce_pdm_build(content, import_name)
        self._enforce_project_metadata(content, project_name, project_version)
        self._normalize_dependencies(content)
        self._ensure_dev_dependencies(content)

        return dumps(content)

    def _enforce_build_system(self, content: dict) -> None:
        from tomlkit import table
        build_tbl = content.get("build-system")
        if not isinstance(build_tbl, dict):
            build_tbl = table()
            content["build-system"] = build_tbl
        build_tbl["requires"] = ["pdm-backend"]
        build_tbl["build-backend"] = "pdm.backend"

    def _enforce_pdm_build(self, content: dict, import_name: str | None) -> None:
        from wexample_filestate_python.helpers.toml import toml_ensure_table
        tool_tbl, _ = toml_ensure_table(content, ["tool"])
        pdm_tbl, _ = toml_ensure_table(tool_tbl, ["pdm"])
        build_pdm_tbl, _ = toml_ensure_table(pdm_tbl, ["build"])

        pdm_tbl["distribution"] = True
        build_pdm_tbl["package-dir"] = "src"
        if import_name:
            build_pdm_tbl["packages"] = [{"include": import_name, "from": "src"}]
            build_pdm_tbl.pop("includes", None)

        # 🔹 Add setuptools exclusion of testing package
        setuptools_tbl, _ = toml_ensure_table(tool_tbl, ["setuptools"])
        find_tbl, _ = toml_ensure_table(setuptools_tbl, ["packages", "find"])
        find_tbl["include"] = ["*"]
        find_tbl["exclude"] = [f"{import_name}.testing*"]

    def _enforce_project_metadata(
            self, content: dict, project_name: str | None, project_version: str | None
    ) -> None:
        from wexample_filestate_python.helpers.toml import toml_ensure_table
        project_tbl, _ = toml_ensure_table(content, ["project"])
        if project_name:
            project_tbl["name"] = project_name
        if project_version:
            project_tbl["version"] = project_version
        project_tbl["requires-python"] = ">=3.10"

    def _normalize_dependencies(self, content: dict) -> None:
        from wexample_filestate_python.helpers.package import package_normalize_name
        from wexample_filestate_python.helpers.toml import (
            toml_get_string_value,
            toml_sort_string_array,
        )
        from wexample_wex_addon_dev_python.const.package import RUNTIME_DEPENDENCY_REMOVE_NAMES

        deps_arr = self._dependencies_array()
        toml_sort_string_array(deps_arr)

        # filter unwanted deps
        def _should_remove(item: object) -> bool:
            name = package_normalize_name(toml_get_string_value(item))
            return name in RUNTIME_DEPENDENCY_REMOVE_NAMES or (
                    name == "typing-extensions"
            )

        deps_arr[:] = [it for it in deps_arr if not _should_remove(it)]
        toml_sort_string_array(deps_arr)

        # normalize attrs/cattrs
        normalized = []
        for it in list(deps_arr):
            base = package_normalize_name(toml_get_string_value(it).strip())
            if base == "attrs":
                normalized.append("attrs>=23.1.0")
            elif base == "cattrs":
                normalized.append("cattrs>=23.1.0")
            else:
                normalized.append(it)
        if normalized:
            deps_arr[:] = normalized
            toml_sort_string_array(deps_arr)

        # ensure they are present
        names = {package_normalize_name(toml_get_string_value(it)) for it in deps_arr}
        if "attrs" not in names:
            deps_arr.append("attrs>=23.1.0")
        if "cattrs" not in names:
            deps_arr.append("cattrs>=23.1.0")
        toml_sort_string_array(deps_arr)

    def _ensure_dev_dependencies(self, content: dict) -> None:
        from wexample_filestate_python.helpers.package import package_normalize_name
        from wexample_filestate_python.helpers.toml import (
            toml_get_string_value,
            toml_sort_string_array,
        )
        dev_arr = self._optional_group_array("dev")
        deps_arr = self._dependencies_array()

        runtime_pkgs = {
            package_normalize_name(toml_get_string_value(it)) for it in list(deps_arr)
        }
        dev_values = [toml_get_string_value(it).strip() for it in list(dev_arr)]

        for pkg in ["pytest", "pytest-cov"]:
            if pkg not in runtime_pkgs and pkg not in dev_values:
                dev_arr.append(pkg)

        toml_sort_string_array(dev_arr)


    def find_package_workdir(self) -> CodeBaseWorkdir | None:
        from wexample_wex_core.workdir.code_base_workdir import CodeBaseWorkdir

        return self.find_closest(CodeBaseWorkdir)

    def list_dependencies(
        self, optional: bool = False, group: str = "dev"
    ) -> list[str]:
        deps = self._get_deps_array(optional=optional, group=group)
        return [str(x) for x in list(deps)]

    def list_dependency_names(
        self,
        canonicalize_names: bool = True,
        optional: bool = False,
        group: str = "dev",
    ) -> list[str]:
        """Return dependency package names derived from list_dependencies().

        If canonicalize_names is True, names are normalized using packaging's
        canonicalize_name for robust comparisons (dash/underscore, case, etc.).
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        names: list[str] = []
        for spec in self.list_dependencies(optional=optional, group=group):
            try:
                name = Requirement(spec).name
                names.append(canonicalize_name(name) if canonicalize_names else name)
            except Exception:
                # Skip unparsable entries when deriving names
                continue
        return names

    def remove_dependency_by_name(
        self, package_name: str, optional: bool = False, group: str = "dev"
    ) -> bool:
        """Remove all dependency entries that match the given package name.

        The provided package_name can be raw; it will be canonicalized to ensure
        consistent matching against entries parsed from list_dependencies().
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        deps = self._get_deps_array(optional=optional, group=group)

        target = canonicalize_name(package_name)
        filtered: list[str] = []
        for existing in list(deps):
            try:
                existing_name = canonicalize_name(Requirement(str(existing)).name)
            except Exception:
                # Keep unparsable entries untouched
                filtered.append(existing)
                continue
            if existing_name != target:
                filtered.append(existing)

        if len(filtered) != len(deps):
            deps.clear()
            deps.extend(filtered)
            return True
        return False

    def _dependencies_array(self):
        """Ensure and return project.dependencies as a multi-line TOML array."""
        from wexample_filestate_python.helpers.toml import toml_ensure_array

        project = self._project_table()
        deps, _ = toml_ensure_array(project, "dependencies")
        deps.multiline(True)
        return deps

    # --- Unified dependency accessors (runtime vs optional) ---
    def _get_deps_array(self, optional: bool = False, group: str = "dev"):
        """Return TOML array for runtime deps or optional group (multiline)."""
        return (
            self._optional_group_array(group)
            if optional
            else self._dependencies_array()
        )

    def _optional_group_array(self, group: str):
        """Ensure and return project.optional-dependencies[group] as multi-line array."""
        from wexample_filestate_python.helpers.toml import (
            toml_ensure_array,
            toml_ensure_table,
        )

        project = self._project_table()
        opt, _ = toml_ensure_table(project, ["optional-dependencies"])
        arr, _ = toml_ensure_array(opt, group)
        arr.multiline(True)
        return arr

    def _project_table(self):
        """Ensure and return the [project] table."""
        from wexample_filestate_python.helpers.toml import toml_ensure_table

        doc = self.read_parsed()
        project, _ = toml_ensure_table(doc, ["project"])
        return project
