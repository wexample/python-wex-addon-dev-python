from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from wexample_config.const.types import DictConfig
from wexample_wex_addon_app.workdir.framework_packages_suite_workdir import (
    FrameworkPackageSuiteWorkdir,
)

if TYPE_CHECKING:
    from wexample_wex_addon_dev_python.workdir.python_package_workdir import PythonPackageWorkdir


class PythonPackagesSuiteWorkdir(FrameworkPackageSuiteWorkdir):
    def packages_harmonize_versions(self):
        dependencies_map = self.build_dependencies_map()
        for package_name in dependencies_map:
            package = self.get_package(package_name)

            for package_name_search in dependencies_map:
                searched_package = self.get_package(package_name_search)
                if package.imports_package_in_codebase(searched_package):
                    self.build_dependencies_stack(
                        package,
                        searched_package,
                        dependencies_map
                    )

                    pass

        # for package in self.get_packages():
        #     self.io.log(f'Publishing package {package.get_project_name()}')
        #     self.io.indentation_up()
        #     self.io.success(f'Package {package.get_project_name()}')
        #     self.io.indentation_down()

    def build_dependencies_stack(
            self,
            package: PythonPackageWorkdir,
            dependency: PythonPackageWorkdir,
            dependencies_map: dict[str, list[str]],
    ) -> list[PythonPackageWorkdir]:
        """Return the declared dependency chain from `package` to `dependency`.

        We search a path using the declared local dependency map (dependencies_map),
        so each hop is an explicit dependency declared in pyproject.toml.
        If a path exists, returns the list of package objects forming the chain
        [start=package, ..., end=dependency]. If no path, returns [].
        """

        start = package.get_package_name()
        target = dependency.get_package_name()

        # Fast path
        if start == target:
            return [package]

        # Deterministic DFS to find one path from start -> target
        visited: set[str] = set()

        def dfs(curr: str, path: list[str]) -> list[str] | None:
            if curr == target:
                return path
            visited.add(curr)
            # Sort neighbors for determinism
            for nxt in sorted(dependencies_map.get(curr, [])):
                if nxt in visited:
                    continue
                found = dfs(nxt, path + [nxt])
                if found is not None:
                    return found
            return None

        name_path = dfs(start, [start])
        if not name_path:
            return []

        # Convert names to package objects, filtering out any missing (shouldn't happen)
        stack: list[PythonPackageWorkdir] = []
        for name in name_path:
            pkg = self.get_package(name)
            if pkg is not None:
                stack.append(pkg)  # type: ignore[assignment]

        # Ensure the last element is the requested dependency package object
        if stack and stack[-1].get_package_name() == target:
            return stack
        return []

    def build_ordered_dependencies(self) -> list[str]:
        # Build and validate the dependency map, then compute a stable topological order
        return self.topological_order(
            self.build_dependencies_map()
        )

    def topological_order(self, dep_map: dict[str, list[str]]) -> list[str]:
        """
        Deterministic Kahn topological sort.
        Returns an order from leaves (no deps) to trunk (most depended on).
        Raises ValueError on cycles.
        """
        # Build reverse adjacency: dep -> [dependents]
        dependents: dict[str, list[str]] = {name: [] for name in dep_map}
        for pkg, deps in dep_map.items():
            for d in deps:
                if d in dependents:
                    dependents[d].append(pkg)

        # In-degree is number of local deps
        in_degree: dict[str, int] = {name: len(deps) for name, deps in dep_map.items()}

        # Start with leaves (in_degree == 0), keep deterministic ordering
        queue: list[str] = sorted([name for name, deg in in_degree.items() if deg == 0])

        ordered: list[str] = []
        while queue:
            node = queue.pop(0)
            ordered.append(node)
            for depd in sorted(dependents.get(node, [])):
                in_degree[depd] -= 1
                if in_degree[depd] == 0:
                    queue.append(depd)
                    queue.sort()

        if len(ordered) != len(dep_map):
            cyclic = [n for n, deg in in_degree.items() if deg > 0]
            raise ValueError(f"Cyclic dependencies detected among: {', '.join(sorted(cyclic))}")

        return ordered

    def get_ordered_packages(self) -> list[PythonPackageWorkdir]:
        """Return package objects ordered leaves -> trunk."""
        order = self.build_ordered_dependencies()
        by_name = {p.get_package_name(): p for p in self.get_packages()}
        return [by_name[n] for n in order]

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_filestate.config_option.children_filter_config_option import (
            ChildrenFilterConfigOption,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_wex_addon_dev_python.workdir.python_package_workdir import (
            PythonPackageWorkdir,
        )

        raw_value = super().prepare_value(raw_value=raw_value)

        children = raw_value["children"]

        # By default, consider each sub folder as a pip package
        children.append(
            {
                "name": "pip",
                "type": DiskItemType.DIRECTORY,
                "children": [
                    ChildrenFilterConfigOption(
                        filter=self._has_pyproject,
                        pattern={
                            "class": PythonPackageWorkdir,
                            "type": DiskItemType.DIRECTORY,
                        },
                    )
                ],
            }
        )

        return raw_value

    def _has_pyproject(self, entry: Path) -> bool:
        return entry.is_dir() and (entry / "pyproject.toml").is_file()
