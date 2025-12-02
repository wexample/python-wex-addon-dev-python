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

    def _child_is_package_directory(self, entry: Path) -> bool:
        return entry.is_dir() and (entry / "pyproject.toml").is_file()

    def _get_children_package_directory_name(self) -> str:
        return "pip"

    def _get_children_package_workdir_class(self) -> type[CodeBaseWorkdir]:
        from wexample_wex_addon_dev_python.workdir.python_package_workdir import (
            PythonPackageWorkdir,
        )

        return PythonPackageWorkdir
