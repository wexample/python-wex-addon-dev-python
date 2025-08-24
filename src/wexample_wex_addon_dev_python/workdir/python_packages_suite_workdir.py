from __future__ import annotations

from pathlib import Path

from wexample_config.const.types import DictConfig
from wexample_wex_addon_app.workdir.framework_packages_suite_workdir import (
    FrameworkPackageSuiteWorkdir,
)
from wexample_wex_addon_dev_python.workdir.python_package_workdir import PythonPackageWorkdir


class PythonPackagesSuiteWorkdir(FrameworkPackageSuiteWorkdir):
    def publish_suite(self):
        ordered_dependencies = self.build_ordered_dependencies()
        # for package in self.get_packages():
        #     self.io.log(f'Publishing package {package.get_project_name()}')
        #     self.io.indentation_up()
        #     self.io.success(f'Package {package.get_project_name()}')
        #     self.io.indentation_down()

    def build_ordered_dependencies(self):
        # Build and validate the dependency map, then compute a stable topological order
        dep_map = self.build_dependencies()
        self.validate_internal_dependencies(dep_map)
        return self.topological_order(dep_map)

    def build_dependencies(self) -> dict[str, list[str]]:
        dependencies = {}
        for package in self.get_packages():
            dependencies[package.get_package_name()] = self.filter_local_packages(package.get_dependencies())

        return dependencies

    def get_local_packages_names(self) -> list[str]:
        return [p.get_package_name() for p in self.get_packages()]

    def filter_local_packages(self, packages: list[str]) -> list[str]:
        """
        Keep only dependencies that are local to this workspace.

        A local dependency is one whose package name matches one of the packages
        discovered by get_packages().
        """
        # Use the dedicated helper to retrieve local package names
        local_names = set(self.get_local_packages_names())
        if not packages:
            return []
        # Return only those present locally, preserve order and remove duplicates
        seen: set[str] = set()
        filtered: list[str] = []
        for name in packages:
            if name in local_names and name not in seen:
                seen.add(name)
                filtered.append(name)
        return filtered

    def validate_internal_dependencies(self, dep_map: dict[str, list[str]]) -> None:
        """
        Ensure all referenced internal dependencies exist among local packages.
        Raises ValueError on unknown references.
        """
        local = set(dep_map.keys())
        unknown: set[str] = set()
        for deps in dep_map.values():
            for d in deps:
                if d not in local:
                    unknown.add(d)
        if unknown:
            raise ValueError(f"Unknown internal dependencies referenced: {', '.join(sorted(unknown))}")

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

    def get_packages(self) -> list[PythonPackageWorkdir]:
        pip_dir = self.find_by_name(item_name='pip')
        if pip_dir:
            return pip_dir.get_children_list()
        return []

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
