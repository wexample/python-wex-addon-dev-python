from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.item.file.toml_file import TomlFile
from wexample_wex_core.workdir.mixin.as_suite_package_item import (
    AsSuitePackageItem,
)

if TYPE_CHECKING:
    from tomlkit import TOMLDocument


class PythonPackageTomlFile(AsSuitePackageItem, TomlFile):
    _content_cache: TOMLDocument | None = None

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
        from wexample_filestate_python.helpers.toml import (
            toml_ensure_table,
            toml_ensure_array,
            toml_sort_string_array,
        )

        doc = self._content_cache
        project, _ = toml_ensure_table(doc, ["project"])
        deps, _ = toml_ensure_array(project, "dependencies")
        if spec not in deps:
            deps.append(spec)
            toml_sort_string_array(deps)

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
        from wexample_filestate_python.helpers.toml import (
            toml_ensure_table,
            toml_ensure_array,
            toml_sort_string_array,
        )

        doc = self._content_cache
        project, _ = toml_ensure_table(doc, ["project"])
        opt, _ = toml_ensure_table(project, ["optional-dependencies"])
        arr, _ = toml_ensure_array(opt, group)
        if spec not in arr:
            arr.append(spec)
            toml_sort_string_array(arr)

    def set_python_requires(self, spec: str) -> None:
        from wexample_filestate_python.helpers.toml import toml_ensure_table

        doc = self._content_cache
        project, _ = toml_ensure_table(doc, ["project"])
        if project.get("requires-python") != spec:
            project["requires-python"] = spec

    def ensure_build_system_pdm(self) -> None:
        from wexample_filestate_python.helpers.toml import toml_ensure_table

        doc = self._content_cache
        build, _ = toml_ensure_table(doc, ["build-system"])
        # Minimal deterministic config
        build["requires"] = ["pdm-backend"]
        build["build-backend"] = "pdm.backend"
