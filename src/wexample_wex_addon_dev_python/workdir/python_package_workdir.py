from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from wexample_filestate.const.disk import DiskItemType
from wexample_wex_addon_app.helpers.python import (
    python_install_dependency_in_venv,
    python_is_package_installed_editable_in_venv,
)

from wexample_wex_addon_dev_python.workdir.python_workdir import PythonWorkdir

if TYPE_CHECKING:
    from wexample_config.const.types import DictConfig
    from wexample_filestate.config_value.readme_content_config_value import (
        ReadmeContentConfigValue,
    )
    from wexample_filestate.utils.search_result import SearchResult
    from wexample_wex_addon_app.workdir.framework_packages_suite_workdir import (
        FrameworkPackageSuiteWorkdir,
    )


class PythonPackageWorkdir(PythonWorkdir):
    _project_info_cache = None

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_helpers.helpers.array import array_dict_get_by

        raw_value = super().prepare_value(raw_value=raw_value)
        children = raw_value.get("children")

        children.append(
            {
                "name": "examples",
                "type": DiskItemType.DIRECTORY,
                "should_exist": True,
                "children": [
                    {
                        "name": "__main__.py",
                        "type": DiskItemType.FILE,
                        "should_exist": True,
                    },
                ],
            },
        )

        # Retrieve the '.gitignore' configuration or create it if it doesn't exist
        config_gitignore = array_dict_get_by("name", ".gitignore", children)
        if config_gitignore is not None:
            generic_gitignore_rules = {
                "Python artifacts": [
                    "*.egg-info",
                    "__pycache__/",
                    "*.py[cod]",
                    "*.pyo",
                ],
                "Build directories": [
                    "/build/",
                    "/dist/",
                    "/pip-wheel-metadata/",
                ],
                "Virtual environments": [
                    ".env",
                    ".venv",
                    "venv/",
                ],
                "Test and coverage artifacts": [
                    ".tox/",
                    ".mypy_cache/",
                    "pytest_cache/",
                    ".coverage",
                    "htmlcov/",
                ],
                "Editor and IDE settings": [
                    ".vscode/",
                    ".idea/",
                    "*.swp",
                    "*~",
                ],
            }

            should_contain_lines = config_gitignore.setdefault(
                "should_contain_lines", []
            )
            if not isinstance(should_contain_lines, list):
                raise ValueError("'should_contain_lines' must be a list")

            for category, rules in generic_gitignore_rules.items():
                category_header = f"# {category}"
                if category_header not in should_contain_lines:
                    should_contain_lines.append(category_header)

                for rule in rules:
                    if rule not in should_contain_lines:
                        should_contain_lines.append(rule)

        return raw_value

    def search_imports_in_codebase(
        self, searched_package: PythonPackageWorkdir
    ) -> list[SearchResult]:
        """Find import statements that reference the given package.

        Supports common Python forms:
        - from <pkg>(.<sub>)* import ...
        - import <pkg>(.<sub>)* [as alias]

        Returns a list of SearchResult with file, line and column for each match.
        """
        import re

        pkg = searched_package.get_package_import_name()
        pattern = (
            rf"(?m)^\s*(?:"
            rf"from\s+{re.escape(pkg)}(?:\.[\w\.]+)?\s+import\s+"
            rf"|import\s+{re.escape(pkg)}(?:\.[\w\.]+)?(?:\s+as\s+\w+)?\b"
            rf")"
        )
        return self.search_in_codebase(pattern, regex=True, flags=re.MULTILINE)

    def search_in_codebase(
        self, string: str, *, regex: bool = False, flags: int = 0
    ) -> list[SearchResult]:
        from wexample_filestate.utils.search_result import SearchResult
        from wexample_filestate_python.file.python_file import PythonFile

        found = []

        def _search(item: PythonFile) -> None:
            found.extend(
                SearchResult.create_for_all_matches(
                    string, item, regex=regex, flags=flags
                )
            )

        self.for_each_child_of_type_recursive(callback=_search, class_type=PythonFile)

        return found

    def _collect_suite_dependencies(
        self,
        direct_dependencies: list[str],
        suite_workdir,
        suite_package_names: set[str],
    ) -> list:
        """Collect all suite packages recursively that need to be installed in editable mode.

        Returns a list of suite package objects ordered leaf -> trunk.
        """
        suite_deps_to_install = set()
        visited = set()

        def collect_recursive(dep_names: list[str]) -> None:
            for dep_name in dep_names:
                if dep_name in visited:
                    continue
                visited.add(dep_name)

                if dep_name in suite_package_names:
                    # This is a suite package, add it and recurse into its dependencies
                    suite_deps_to_install.add(dep_name)
                    pkg = suite_workdir.get_package(dep_name)
                    if pkg:
                        # Get dependencies of this suite package and recurse
                        pkg_dependencies = pkg.list_dependencies_names()
                        collect_recursive(pkg_dependencies)

        # Start with direct dependencies from pyproject.toml
        collect_recursive(direct_dependencies)

        # Order suite packages by dependency (leaf -> trunk)
        all_ordered_packages = suite_workdir.get_ordered_packages()
        suite_deps_ordered = [
            pkg
            for pkg in all_ordered_packages
            if pkg.get_package_name() in suite_deps_to_install
        ]

        return suite_deps_ordered

    def _get_readme_content(self) -> ReadmeContentConfigValue | None:
        from wexample_wex_addon_dev_python.config_value.python_package_readme_config_value import (
            PythonPackageReadmeContentConfigValue,
        )

        return PythonPackageReadmeContentConfigValue(workdir=self)

    def _get_suite_package_workdir_class(self) -> type[FrameworkPackageSuiteWorkdir]:
        from wexample_wex_addon_dev_python.workdir.python_packages_suite_workdir import (
            PythonPackagesSuiteWorkdir,
        )

        return PythonPackagesSuiteWorkdir

    def _install_dependencies_in_venv(
        self, venv_path: Path, env: str | None = None, force: bool = False
    ) -> None:
        from wexample_app.const.env import ENV_NAME_LOCAL
        from wexample_wex_addon_app.helpers.python import (
            python_install_dependencies_in_venv,
        )

        suite_workdir = self.get_shallow_suite_workdir()
        toml_file = self.get_app_config_file()

        # Check for suite only in local env.
        if env == ENV_NAME_LOCAL:
            # Package is part of a suite that may have a venv configured.
            if suite_workdir:
                # Get all dependencies from pyproject.toml
                pyproject_toml_dependencies = toml_file.list_dependencies_names()

                # Get all packages from the suite ordered by dependencies (leaf -> trunk)
                suite_packages = suite_workdir.get_ordered_packages()
                suite_package_names = {pkg.get_package_name() for pkg in suite_packages}

                # Collect all suite packages that need to be installed (including transitive dependencies)
                suite_dependencies_ordered = self._collect_suite_dependencies(
                    pyproject_toml_dependencies, suite_workdir, suite_package_names
                )

                # External dependencies are those not in the suite
                external_dependencies = [
                    dep
                    for dep in pyproject_toml_dependencies
                    if dep not in suite_package_names
                ]

                self.subtitle(
                    f"Installing {len(external_dependencies)} external packages",
                    indentation=1,
                )
                python_install_dependencies_in_venv(
                    venv_path=venv_path, names=external_dependencies
                )

                # Install suite packages in editable mode (leaf -> trunk order)
                if suite_dependencies_ordered:
                    self.subtitle(
                        f"Installing {len(suite_dependencies_ordered)} suite packages in editable mode (leaf -> trunk)",
                        indentation=1,
                    )

                    editable_paths = []

                    for pkg in suite_dependencies_ordered:
                        pkg_path = pkg.get_path()
                        pkg_name = pkg.get_package_name()

                        if force or not python_is_package_installed_editable_in_venv(
                            venv_path=venv_path,
                            package_name=pkg_name,
                            package_path=pkg_path,
                        ):
                            editable_paths.append(str(pkg_path))

                    python_install_dependencies_in_venv(
                        venv_path=venv_path,
                        names=editable_paths,
                        editable=True,
                    )

                self.subtitle(
                    "Installing dev group dependencies",
                    indentation=1,
                )
                python_install_dependencies_in_venv(
                    venv_path=venv_path,
                    names=self.get_app_config_file().optional_group_array(group="dev"),
                )

            self.subtitle(
                "Installing itself in editable mode",
                indentation=1,
            )

            # Install itself as editable.
            python_install_dependency_in_venv(
                venv_path=venv_path, name=self.get_path(), editable=True
            )

            return

        # Fallback to parent behaviour
        super()._install_dependencies_in_venv(venv_path=venv_path, env=env, force=force)

    def _publish(self, force: bool = False) -> None:
        from wexample_filestate_python.common.pipy_gateway import PipyGateway
        from wexample_helpers.helpers.shell import shell_run

        client = PipyGateway(parent_io_handler=self)

        package_name = self.get_package_name()
        version = self.get_project_version()
        if client.package_release_exists(package_name=package_name, version=version):
            self.warning(
                f'Trying to publish an existing release for package "{package_name}" version {version}'
            )
        else:
            # Map token to PyPI's token-based authentication if provided
            username = "__token__"
            password = self.get_env_parameter_or_suite_fallback("PIPY_TOKEN")

            # Build the publish command, adding credentials only when given
            publish_cmd = ["pdm", "publish"]
            if username is not None:
                publish_cmd += ["--username", username]
            if password is not None:
                publish_cmd += ["--password", password]

            shell_run(publish_cmd, inherit_stdio=True, cwd=self.get_path())
