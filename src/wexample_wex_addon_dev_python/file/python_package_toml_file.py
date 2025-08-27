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
    _content_cache: TOMLDocument | None = None

    def _project_table(self):
        """Ensure and return the [project] table."""
        from wexample_filestate_python.helpers.toml import toml_ensure_table

        doc = self._content_cache
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

    def list_dependencies(self) -> list[str]:
        deps = self._dependencies_array()
        return [str(x) for x in list(deps)]

    def list_dependency_names(self, canonicalize_names: bool = True) -> list[str]:
        """Return dependency package names derived from list_dependencies().

        If canonicalize_names is True, names are normalized using packaging's
        canonicalize_name for robust comparisons (dash/underscore, case, etc.).
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        names: list[str] = []
        for spec in self.list_dependencies():
            try:
                name = Requirement(spec).name
                names.append(canonicalize_name(name) if canonicalize_names else name)
            except Exception:
                # Skip unparsable entries when deriving names
                continue
        return names

    def add_dependency(self, spec: str) -> None:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
        from wexample_filestate_python.helpers.toml import toml_sort_string_array

        deps = self._dependencies_array()
        # Remove existing entries for the same package name before adding the new spec.
        try:
            new_name = canonicalize_name(Requirement(spec).name)
            self.remove_dependency_by_name(new_name)
        except Exception:
            # If parsing fails, we won't attempt name-based removal.
            pass

        # Append (or re-append) the new spec if it is not already present verbatim
        if spec not in deps:
            deps.append(spec)
        toml_sort_string_array(deps)

    def remove_dependency_by_name(self, package_name: str) -> None:
        """Remove all dependency entries that match the given package name.

        The provided package_name can be raw; it will be canonicalized to ensure
        consistent matching against entries parsed from list_dependencies().
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        deps = self._dependencies_array()

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

    def list_optional_dependencies(self, group: str) -> list[str]:
        arr = self._optional_group_array(group)
        return [str(x) for x in list(arr)]

    def list_optional_dependency_names(
            self, group: str, canonicalize_names: bool = True
    ) -> list[str]:
        """Return only the package names for a given optional dependency group.

        Mirrors list_dependency_names() behavior by parsing requirement specs
        and (optionally) canonicalizing names.
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        names: list[str] = []
        for spec in self.list_optional_dependencies(group):
            try:
                name = Requirement(spec).name
                names.append(canonicalize_name(name) if canonicalize_names else name)
            except Exception:
                # Skip unparsable entries when deriving names
                continue
        return names

    def add_optional_dependency(self, group: str, spec: str) -> None:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
        from wexample_filestate_python.helpers.toml import toml_sort_string_array

        arr = self._optional_group_array(group)
        # Remove existing entries for the same package name before adding the new spec.
        try:
            new_name = canonicalize_name(Requirement(spec).name)
            self.remove_optional_dependency_by_name(group, new_name)
        except Exception:
            # If parsing fails, we won't attempt name-based removal.
            pass

        # Append (or re-append) the new spec if it is not already present verbatim
        if spec not in arr:
            arr.append(spec)
        toml_sort_string_array(arr)

    def remove_optional_dependency_by_name(self, group: str, package_name: str) -> None:
        """Remove all optional dependency entries in a group matching a name.

        Name matching is canonicalized to ensure robust comparisons.
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        arr = self._optional_group_array(group)

        target = canonicalize_name(package_name)
        filtered: list[str] = []
        for existing in list(arr):
            try:
                existing_name = canonicalize_name(Requirement(str(existing)).name)
            except Exception:
                # Keep unparsable entries untouched
                filtered.append(existing)
                continue
            if existing_name != target:
                filtered.append(existing)

        if len(filtered) != len(arr):
            arr.clear()
            arr.extend(filtered)

    def find_package_workdir(self) -> FrameworkPackageWorkdir | None:
        from wexample_wex_core.workdir.framework_package_workdir import (
            FrameworkPackageWorkdir,
        )

        return self.find_closest(FrameworkPackageWorkdir)

    def writable(self, content: TOMLDocument | dict | None = None) -> str:
        """Serialize a TOMLDocument (preferred) or a plain dict to TOML.
        Using tomlkit.dumps preserves comments/formatting when content is a TOMLDocument.
        """
        from tomlkit import dumps

        content = content or self.read()

        package = self.find_package_workdir()
        if package:
            content["project"]["name"] = package.get_package_name()

        return dumps(content)
