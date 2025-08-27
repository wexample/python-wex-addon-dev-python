from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.item.file.toml_file import TomlFile
from wexample_wex_core.workdir.mixin.as_suite_package_item import (
    AsSuitePackageItem,
)

if TYPE_CHECKING:
    from tomlkit import TOMLDocument
    from wexample_wex_core.workdir.framework_package_workdir import (
        FrameworkPackageWorkdir,
    )


class PythonPackageTomlFile(AsSuitePackageItem, TomlFile):

    def _project_table(self):
        """Ensure and return the [project] table."""
        from wexample_filestate_python.helpers.toml import toml_ensure_table

        doc = self.read_parsed()
        project, _ = toml_ensure_table(doc, ["project"])
        return project

    def _dependencies_array(self):
        """Ensure and return project.dependencies as a multi-line TOML array."""
        from wexample_filestate_python.helpers.toml import (
            toml_ensure_array,
        )

        project = self._project_table()
        deps, _ = toml_ensure_array(project, "dependencies")
        deps.multiline(True)
        return deps

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

    # --- Unified dependency accessors (runtime vs optional) ---
    def _get_deps_array(self, optional: bool = False, group: str = "dev"):
        """Return TOML array for runtime deps or optional group (multiline)."""
        return (
            self._optional_group_array(group)
            if optional
            else self._dependencies_array()
        )

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

    def add_dependency(
        self, spec: str, optional: bool = False, group: str = "dev"
    ) -> None:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
        from wexample_filestate_python.helpers.toml import toml_sort_string_array

        deps = self._get_deps_array(optional=optional, group=group)
        # Remove existing entries for the same package name before adding the new spec.
        try:
            new_name = canonicalize_name(Requirement(spec).name)
            self.remove_dependency_by_name(new_name, optional=optional, group=group)
        except Exception:
            # If parsing fails, we won't attempt name-based removal.
            pass

        # Append (or re-append) the new spec if it is not already present verbatim
        if spec not in deps:
            deps.append(spec)
        toml_sort_string_array(deps)

    def remove_dependency_by_name(
        self, package_name: str, optional: bool = False, group: str = "dev"
    ) -> None:
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

    def find_package_workdir(self) -> FrameworkPackageWorkdir | None:
        from wexample_wex_core.workdir.framework_package_workdir import (
            FrameworkPackageWorkdir,
        )

        return self.find_closest(FrameworkPackageWorkdir)

    def dumps(self, content: TOMLDocument | dict | None = None) -> str:
        """Serialize a TOMLDocument (preferred) or a plain dict to TOML.
        Using tomlkit.dumps preserves comments/formatting when content is a TOMLDocument.
        """
        from tomlkit import dumps, table
        from wexample_filestate_python.helpers.package import package_normalize_name
        from wexample_filestate_python.helpers.toml import (
            toml_ensure_array_multiline,
            toml_ensure_table,
            toml_get_string_value,
            toml_set_array_multiline,
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
        includes_arr, _ = toml_ensure_array_multiline(build_pdm_tbl, "includes")

        pdm_tbl["distribution"] = True
        # Enforce src layout, packages, and includes (py.typed)
        if build_pdm_tbl.get("package-dir") != "src":
            build_pdm_tbl["package-dir"] = "src"
        if import_name:
            desired_pkgs = [{"include": import_name, "from": "src"}]
            if build_pdm_tbl.get("packages") != desired_pkgs:
                build_pdm_tbl["packages"] = desired_pkgs
            desired_includes = [f"src/{import_name}/py.typed"]
            current_includes = [str(x) for x in list(includes_arr)]
            if current_includes != desired_includes:
                toml_set_array_multiline(build_pdm_tbl, "includes", desired_includes)

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
                # Safe to drop when python >= 3.10 and we manage deps
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

        # Normalize any pydantic spec to pydantic>=2,<3
        normalized = False
        new_deps = []
        for it in list(deps_arr):
            val = toml_get_string_value(it).strip()
            base = package_normalize_name(val)
            if base == "pydantic":
                new_deps.append("pydantic>=2,<3")
                normalized = True
            else:
                new_deps.append(it)
        if normalized:
            deps_arr.clear()
            deps_arr.extend(new_deps)
            toml_sort_string_array(deps_arr)

        # Ensure pydantic>=2,<3 present unless excluded
        existing_norm = {
            package_normalize_name(toml_get_string_value(it)) for it in list(deps_arr)
        }
        if "pydantic" not in exclude_add and "pydantic" not in existing_norm:
            deps_arr.append("pydantic>=2,<3")
            toml_sort_string_array(deps_arr)

        # Ensure optional dev group contains pytest unless already in runtime deps
        runtime_has_pytest = any(
            package_normalize_name(toml_get_string_value(it)) == "pytest"
            for it in list(deps_arr)
        )
        dev_values = [toml_get_string_value(it) for it in list(dev_arr)]
        if not runtime_has_pytest and not any(
            v.strip() == "pytest" for v in dev_values
        ):
            dev_arr.append("pytest")
            toml_sort_string_array(dev_arr)

        return dumps(content)
