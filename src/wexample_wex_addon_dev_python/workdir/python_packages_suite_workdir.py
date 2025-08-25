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
                imports = package.search_imports_in_codebase(searched_package)
                if len(imports) > 0:
                    dependencies_stack = self.build_dependencies_stack(
                        package,
                        searched_package,
                        dependencies_map
                    )

                    if len(dependencies_stack) == 0:
                        # Build a readable list of import locations to help debugging
                        imports_details = "\n".join(
                            f" - {res.item.get_path()}:{res.line}:{res.column} (searched='{res.searched}')"
                            for res in imports
                        )
                        raise AssertionError(
                            (
                                "Dependency violation: package \"{pkg}\" imports code from \"{dep}\" "
                                "but there is no declared local dependency path. "
                                "Add \"{dep}\" to the 'project.dependencies' of \"{pkg}\" in its pyproject.toml, "
                                "or declare an intermediate local package that depends on \"{dep}\".\n\n"
                                "Detected import locations (file:line:col):\n{locations}"
                            ).format(
                                pkg=package_name,
                                dep=package_name_search,
                                locations=imports_details or " - <no locations captured>"
                            )
                        )

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

        Uses NetworkX (if available) to build a directed graph of local declared
        dependencies and compute a shortest path from `package` to `dependency`.
        Falls back to an internal deterministic DFS if NetworkX is not installed.
        Returns a list of PythonPackageWorkdir objects [package, ..., dependency],
        or an empty list if no path exists.
        """

        start = package.get_package_name()
        target = dependency.get_package_name()

        # Trivial case
        if start == target:
            return [package]

        import networkx as nx

        # Build a deterministic DiGraph: add nodes/edges in sorted order
        nodes = set(dependencies_map.keys()) | {d for deps in dependencies_map.values() for d in deps}
        G = nx.DiGraph()
        for n in sorted(nodes):
            G.add_node(n)
        for src in sorted(dependencies_map.keys()):
            for dst in sorted(dependencies_map.get(src, [])):
                if dst in nodes:
                    G.add_edge(src, dst)

        if not (G.has_node(start) and G.has_node(target)):
            return []

        try:
            name_path = nx.shortest_path(G, source=start, target=target)
        except nx.NetworkXNoPath:
            return []

        # Convert path of names to concrete package objects
        stack: list[PythonPackageWorkdir] = []
        for name in name_path:
            pkg = self.get_package(name)
            if pkg is not None:
                stack.append(pkg)

        return stack if stack and stack[-1].get_package_name() == target else []

    def build_ordered_dependencies(self) -> list[str]:
        # Build and validate the dependency map, then compute a stable topological order
        return self.topological_order(
            self.build_dependencies_map()
        )

    def topological_order(self, dep_map: dict[str, list[str]]) -> list[str]:
        """Deterministic topological order using graphlib.TopologicalSorter.
        Returns a leaves -> trunk order (dependencies before dependents).
        Raises ValueError on cycles.
        """
        from graphlib import TopologicalSorter, CycleError

        # Normalize: include every mentioned node and sort for stable results
        nodes = set(dep_map.keys()) | {d for deps in dep_map.values() for d in deps}
        normalized: dict[str, list[str]] = {
            k: sorted([d for d in dep_map.get(k, []) if d in nodes])
            for k in sorted(nodes)
        }

        ts = TopologicalSorter()
        for k, deps in normalized.items():
            ts.add(k, *deps)

        try:
            order = list(ts.static_order())
        except CycleError as e:
            # Extract involved nodes if present, otherwise a generic message
            msg = getattr(e, 'args', [None])[0] or 'Cyclic dependencies detected'
            raise ValueError(str(msg)) from e

        # Return only local packages (original keys of dep_map)
        return [n for n in order if n in dep_map]

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
