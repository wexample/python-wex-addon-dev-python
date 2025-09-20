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
        from tomlkit import dumps, table
        from wexample_filestate_python.helpers.package import package_normalize_name
        from wexample_filestate_python.helpers.toml import (
            toml_ensure_table,
            toml_get_string_value,
            toml_sort_string_array,
        )
        from wexample_wex_addon_dev_python.const.package import (
            RUNTIME_DEPENDENCY_REMOVE_NAMES,
        )

        # Obtain the current TOML document (preserving formatting) if not provided
        content = content or self.read_parsed()

        # Try to get current package/workdir context
        package = self.find_package_workdir()
        import_name: str | None = None
        project_version: str | None = None
        project_name: str | None = None
        if package:
            project_name = package.get_package_name()
            project_version = package.get_project_version()
            import_name = package.get_package_import_name()

        # --- [build-system] enforcement ---
        build_tbl = content.get("build-system") if isinstance(content, dict) else None
        if not build_tbl or not isinstance(build_tbl, dict):
            build_tbl = table()
            content["build-system"] = build_tbl
        desired_requires = ["pdm-backend"]
        if build_tbl.get("requires") != desired_requires:
            build_tbl["requires"] = desired_requires
        if build_tbl.get("build-backend") != "pdm.backend":
            build_tbl["build-backend"] = "pdm.backend"

        # --- [tool.pdm.build] enforcement ---
        tool_tbl, _ = toml_ensure_table(content, ["tool"])
        pdm_tbl, _ = toml_ensure_table(tool_tbl, ["pdm"])
        build_pdm_tbl, _ = toml_ensure_table(pdm_tbl, ["build"])

        pdm_tbl["distribution"] = True
        # Enforce src layout and packages (remove includes to avoid conflicts)
        if build_pdm_tbl.get("package-dir") != "src":
            build_pdm_tbl["package-dir"] = "src"
        if import_name:
            desired_pkgs = [{"include": import_name, "from": "src"}]
            if build_pdm_tbl.get("packages") != desired_pkgs:
                build_pdm_tbl["packages"] = desired_pkgs
            # Remove includes to avoid conflicts with packages declaration
            if "includes" in build_pdm_tbl:
                del build_pdm_tbl["includes"]

        # --- [project] table and basic fields ---
        project_tbl, _ = toml_ensure_table(content, ["project"])
        # Name sync (best-effort)
        if project_name:
            project_tbl["name"] = project_name
        # Version sync (best-effort)
        if project_version:
            project_tbl["version"] = project_version
        # Python requirement
        target_requires_python = ">=3.10"
        if project_tbl.get("requires-python") != target_requires_python:
            project_tbl["requires-python"] = target_requires_python

        # --- Dependencies normalization ---
        # Use class helper to ensure multiline dependencies array
        deps_arr = self._dependencies_array()
        # Sort dependencies array
        toml_sort_string_array(deps_arr)

        # Optional dependency groups
        opt_tbl, _ = toml_ensure_table(project_tbl, ["optional-dependencies"])
        # Ensure dev group exists (multiline)
        dev_arr = self._optional_group_array("dev")

        # Filestate configuration for keep/exclude-add
        filestate_tbl = None
        if isinstance(tool_tbl, dict):
            filestate_tbl = tool_tbl.get("filestate")
        keep_names: set[str] = set()
        exclude_add: set[str] = set()
        if isinstance(filestate_tbl, dict):
            keep_list = filestate_tbl.get("keep")
            if isinstance(keep_list, list):
                keep_names = {package_normalize_name(str(x)) for x in keep_list}
            ex_list = filestate_tbl.get("exclude-add")
            if isinstance(ex_list, list):
                exclude_add = {str(x).strip().lower() for x in ex_list}

        # Remove unwanted dev/build tools from runtime deps (unless kept)
        def _should_remove(item: object) -> bool:
            name = package_normalize_name(toml_get_string_value(item))
            if name in keep_names:
                return False
            if name == "typing-extensions":
                # Safe to drop when py
                # thon >= 3.10 and we manage deps
                return True
            return name in RUNTIME_DEPENDENCY_REMOVE_NAMES

        to_keep = []
        for it in list(deps_arr):
            if not _should_remove(it):
                to_keep.append(it)
        if len(to_keep) != len(deps_arr):
            deps_arr.clear()
            deps_arr.extend(to_keep)
            toml_sort_string_array(deps_arr)

        # Normalize attrs/cattrs dependencies
        normalized = False
        new_deps = []
        for it in list(deps_arr):
            val = toml_get_string_value(it).strip()
            base = package_normalize_name(val)
            if base == "attrs":
                new_deps.append("attrs>=23.1.0")
                normalized = True
            elif base == "cattrs":
                new_deps.append("cattrs>=23.1.0")
                normalized = True
            else:
                new_deps.append(it)
        if normalized:
            deps_arr.clear()
            deps_arr.extend(new_deps)
            toml_sort_string_array(deps_arr)

        # Ensure attrs and cattrs are present unless excluded
        existing_norm = {
            package_normalize_name(toml_get_string_value(it)) for it in list(deps_arr)
        }
        if "attrs" not in exclude_add and "attrs" not in existing_norm:
            deps_arr.append("attrs>=23.1.0")
            toml_sort_string_array(deps_arr)
        if "cattrs" not in exclude_add and "cattrs" not in existing_norm:
            deps_arr.append("cattrs>=23.1.0")
            toml_sort_string_array(deps_arr)

        # Ensure optional dev group contains required test tools unless already in runtime deps
        required_test_deps = ["pytest", "pytest-cov"]

        runtime_pkgs = {
            package_normalize_name(toml_get_string_value(it))
            for it in list(deps_arr)
        }
        dev_values = [toml_get_string_value(it).strip() for it in list(dev_arr)]

        for pkg in required_test_deps:
            if pkg not in runtime_pkgs and pkg not in dev_values:
                dev_arr.append(pkg)

        toml_sort_string_array(dev_arr)

        return dumps(content)

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
