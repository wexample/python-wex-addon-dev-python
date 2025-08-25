from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.item.file.toml_file import TomlFile
from wexample_filestate_python.helpers.toml import toml_ensure_table, toml_ensure_array
from wexample_helpers.helpers.array import array_sort_in_place
from wexample_wex_core.workdir.mixin.as_suite_package_item import (
    AsSuitePackageItem,
)

if TYPE_CHECKING:
    from tomlkit import TOMLDocument


class PythonPackageTomlFile(AsSuitePackageItem, TomlFile):
    _content_cache: TOMLDocument = None

    def list_dependencies(self) -> list[str]:
        doc = self._content_cache
        project = doc.get("project")
        if not isinstance(project, dict):
            return []
        deps = project.get("dependencies")
        if not isinstance(deps, list):
            return []
        return [str(x) for x in list(deps)]

    def add_dependency(self, spec: str) -> None:
        doc = self._content_cache
        project = toml_ensure_table(doc, "project")
        deps = toml_ensure_array(project, "dependencies")
        if spec not in deps:
            deps.append(spec)
            # Keep list stable/alphabetical for readability
            array_sort_in_place(deps)

    def list_optional_dependencies(self, group: str) -> list[str]:
        doc = self._content_cache
        project = doc.get("project")
        if not isinstance(project, dict):
            return []
        opt = project.get("optional-dependencies")
        if not isinstance(opt, dict):
            return []
        arr = opt.get(group)
        if not isinstance(arr, list):
            return []
        return [str(x) for x in list(arr)]

    def add_optional_dependency(self, group: str, spec: str) -> None:
        doc = self._content_cache
        project = toml_ensure_table(doc, "project")
        opt = toml_ensure_table(project, "optional-dependencies")
        arr = toml_ensure_array(opt, group)
        if spec not in arr:
            arr.append(spec)
            array_sort_in_place(arr)

    def set_python_requires(self, spec: str) -> None:
        doc = self._content_cache
        project = toml_ensure_table(doc, "project")
        if project.get("requires-python") != spec:
            project["requires-python"] = spec

    def ensure_build_system_pdm(self) -> None:
        doc = self._content_cache
        build = toml_ensure_table(doc, "build-system")
        # Minimal deterministic config
        build["requires"] = ["pdm-backend"]
        build["build-backend"] = "pdm.backend"
