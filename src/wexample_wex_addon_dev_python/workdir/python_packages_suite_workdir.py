from __future__ import annotations

from typing import TYPE_CHECKING
from wexample_wex_addon_app.workdir.framework_packages_suite_workdir import (
    FrameworkPackageSuiteWorkdir,
)

if TYPE_CHECKING:
    from pathlib import Path

    from wexample_wex_addon_app.workdir.code_base_workdir import (
        CodeBaseWorkdir,
    )
    from wexample_wex_addon_dev_python.workdir.python_package_workdir import (
        PythonPackageWorkdir,
    )


class PythonPackagesSuiteWorkdir(FrameworkPackageSuiteWorkdir):
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
        nodes = set(dependencies_map.keys()) | {
            d for deps in dependencies_map.values() for d in deps
        }
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
        return self.topological_order(self.build_dependencies_map())

    def get_dependents(
        self, package: PythonPackageWorkdir
    ) -> list[PythonPackageWorkdir]:
        dependents = []
        for neighbor_package in self.get_packages():
            if neighbor_package.depends_from(package):
                dependents.append(neighbor_package)
        return dependents

    def get_ordered_packages(self) -> list[PythonPackageWorkdir]:
        """Return package objects ordered leaves -> trunk."""
        order = self.build_ordered_dependencies()
        by_name = {p.get_package_name(): p for p in self.get_packages()}
        return [by_name[n] for n in order]

    def packages_validate_internal_dependencies_declarations(self) -> None:
        from wexample_wex_addon_app.exception.dependency_violation_exception import DependencyViolationException
        dependencies_map = self.build_dependencies_map()

        self.io.log("Checking packages dependencies consistency...")
        self.io.indentation_up()
        progress = self.io.progress(
            total=len(dependencies_map), print_response=False
        ).get_handle()

        for package_name in dependencies_map:
            package = self.get_package(package_name)

            for package_name_search in dependencies_map:
                searched_package = self.get_package(package_name_search)
                imports = package.search_imports_in_codebase(searched_package)
                if len(imports) > 0:
                    dependencies_stack = self.build_dependencies_stack(
                        package, searched_package, dependencies_map
                    )

                    if len(dependencies_stack) == 0:
                        # Build a readable list of import locations to help debugging
                        import_locations = [
                            f"{res.item.get_path()}:{res.line}:{res.column}"
                            for res in imports
                        ]
                        raise DependencyViolationException(
                            package_name=package_name,
                            imported_package=package_name_search,
                            import_locations=import_locations,
                        )

            progress.advance(label=f"Package {package.get_project_name()}", step=1)

        self.io.success("Internal dependencies match.")
        self.io.indentation_down()

    def topological_order(self, dep_map: dict[str, list[str]]) -> list[str]:
        """Deterministic topological order using graphlib.TopologicalSorter.
        Returns a leaves -> trunk order (dependencies before dependents).
        Raises ValueError on cycles.
        """
        from graphlib import CycleError, TopologicalSorter

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
            msg = getattr(e, "args", [None])[0] or "Cyclic dependencies detected"
            raise ValueError(str(msg)) from e

        # Return only local packages (original keys of dep_map)
        return [n for n in order if n in dep_map]

    def _child_is_package_directory(self, entry: Path) -> bool:
        return entry.is_dir() and (entry / "pyproject.toml").is_file()

    def _get_children_package_directory_name(self) -> str:
        return "pip"

    def _get_children_package_workdir_class(self) -> type[CodeBaseWorkdir]:
        from wexample_wex_addon_dev_python.workdir.python_package_workdir import (
            PythonPackageWorkdir,
        )

        return PythonPackageWorkdir
