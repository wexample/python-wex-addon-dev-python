from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.item.file.toml_file import TomlFile
from wexample_helpers.helpers.array import array_sort_in_place
from wexample_wex_core.workdir.mixin.as_suite_package_item import (
    AsSuitePackageItem,
)

if TYPE_CHECKING:
    from tomlkit import TOMLDocument


class PythonPackageTomlFile(AsSuitePackageItem, TomlFile):
    _content_cache: TOMLDocument = None

    @staticmethod
    def _ensure_table(root: dict, *path: str) -> dict:
        from tomlkit import table

        cur = root
        for key in path:
            val = cur.get(key)
            if not isinstance(val, dict):
                val = table()
                cur[key] = val
            cur = val
        return cur

    @staticmethod
    def _ensure_array(tbl: dict, key: str) -> list:
        from tomlkit import array

        val = tbl.get(key)
        if not isinstance(val, list):
            val = array()
            tbl[key] = val
        return val

    # ---------- public high-level API ----------
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
        project = self._ensure_table(doc, "project")
        deps = self._ensure_array(project, "dependencies")
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
        project = self._ensure_table(doc, "project")
        opt = self._ensure_table(project, "optional-dependencies")
        arr = self._ensure_array(opt, group)
        if spec not in arr:
            arr.append(spec)
            array_sort_in_place(arr)

    def set_python_requires(self, spec: str) -> None:
        doc = self._content_cache
        project = self._ensure_table(doc, "project")
        if project.get("requires-python") != spec:
            project["requires-python"] = spec

    def ensure_build_system_pdm(self) -> None:
        doc = self._content_cache
        build = self._ensure_table(doc, "build-system")
        # Minimal deterministic config
        build["requires"] = ["pdm-backend"]
        build["build-backend"] = "pdm.backend"
