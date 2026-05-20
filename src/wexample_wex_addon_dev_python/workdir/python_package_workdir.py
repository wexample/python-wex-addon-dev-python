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

    def check_publish_prerequisites(self) -> None:
        import shutil

        super().check_publish_prerequisites()

        pdm_build_dir = self.get_path() / ".pdm-build"
        if pdm_build_dir.exists():
            try:
                shutil.rmtree(pdm_build_dir)
            except PermissionError:
                raise RuntimeError(
                    f"Cannot remove '{pdm_build_dir}' (permission denied — likely created by root). "
                    f"Run: sudo rm -rf '{pdm_build_dir}'"
                )

        if not shutil.which("pdm"):
            raise RuntimeError(
                "'pdm' not found in PATH.\n"
                "Install: pipx install pdm — then run: wex core::env/configure"
            )

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_helpers.helpers.array import array_dict_get_by
        from wexample_helpers.helpers.file import file_read
        from wexample_helpers.helpers.module import module_get_path

        import wexample_wex_addon_dev_python

        raw_value = super().prepare_value(raw_value=raw_value)
        children = raw_value.get("children")

        # Add .gitlab-ci.yml for private GitLab registry packages.
        # Both callbacks are evaluated after configure() completes, so base_name
        # and runtime config are fully available at that point.
        children.append(
            {
                "name": ".gitlab-ci.yml",
                "type": DiskItemType.FILE,
                "should_exist": lambda _target, _self=self: bool(
                    _self.search_app_or_suite_runtime_config(
                        "pdm.repository.url", default=None
                    ).get_str_or_none()
                ),
                "content": lambda _: file_read(
                    module_get_path(wexample_wex_addon_dev_python)
                    / "resources"
                    / "package_publish_gitlab.yml"
                ),
            }
        )

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

        children.append(
            {
                "name": ".pdm-build",
                "type": DiskItemType.DIRECTORY,
                "should_exist": True,
                "mode": {"permissions": "755", "owner": "~"},
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
                    "/.pdm-build/",
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

    def _classify_version_bump(self, last_tag: str) -> str:
        from wexample_helpers.const.types import (
            UPGRADE_TYPE_INTERMEDIATE,
            UPGRADE_TYPE_MAJOR,
            UPGRADE_TYPE_MINOR,
        )
        from wexample_helpers_git.helpers.git import git_has_changes_since_tag

        if not git_has_changes_since_tag(last_tag, "src", cwd=self.get_path()):
            return UPGRADE_TYPE_MINOR

        try:
            import griffe

            module_name = self.get_package_name().replace("-", "_")
            repo_path = str(self.get_path())

            previous = griffe.load_git(
                module_name,
                ref=last_tag,
                repo=repo_path,
                search_paths=["src"],
            )
            current = griffe.load(
                module_name,
                search_paths=[str(self.get_path() / "src")],
            )

            if list(griffe.find_breaking_changes(previous, current)):
                return UPGRADE_TYPE_MAJOR

            return UPGRADE_TYPE_INTERMEDIATE

        except Exception:
            return UPGRADE_TYPE_MAJOR

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
                        pkg_dependencies = pkg.get_dependencies_versions().keys()
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

    def _get_critical_directories(self) -> list[str]:
        return ["src"]

    def _get_readme_content(self) -> ReadmeContentConfigValue | None:
        from wexample_wex_addon_dev_python.config_value.python_package_readme_config_value import (
            PythonPackageReadmeContentConfigValue,
        )

        return PythonPackageReadmeContentConfigValue(workdir=self)

    def _get_suite_workdir_class(self) -> type[FrameworkPackageSuiteWorkdir]:
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
                pyproject_toml_dependencies = (
                    toml_file.get_dependencies_versions().keys()
                )

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

    def _post_publish(self) -> None:
        from wexample_helpers_git.const.common import GIT_BRANCH_MAIN

        self.merge_to_main()
        self.push_to_deployment_remote(branch_name=GIT_BRANCH_MAIN)

    def _publish(self, force: bool = False) -> None:
        from wexample_filestate_python.common.pipy_gateway import PipyGateway
        from wexample_helpers.helpers.shell import shell_run
        from wexample_helpers_git.helpers.git import (
            git_push_tag,
            git_tag_annotated,
            git_tag_exists,
        )

        repository_url = self.search_app_or_suite_runtime_config(
            "pdm.repository.url", default=None
        ).get_str_or_none()

        package_name = self.get_package_name()
        version = self.get_setup_version()

        # Private GitLab registry: trigger CI by pushing a git tag
        if repository_url:
            remote = self._get_deployment_remote_name()
            tag = f"v{version}"
            cwd = self.get_path()

            if git_tag_exists(tag, cwd=cwd, inherit_stdio=False):
                self.log(f"Tag {tag} already exists, skipping creation.")
            else:
                git_tag_annotated(tag, f"Release {tag}", cwd=cwd, inherit_stdio=True)

            git_push_tag(tag, cwd=cwd, remote=remote, inherit_stdio=True)
            return

        # TODO: align public PyPI packages with the private registry approach — publish
        #       via a GitLab CI pipeline triggered by a git tag rather than running
        #       `pdm publish` locally.
        # PyPI public: publish locally
        client = PipyGateway(parent_io_handler=self)
        if client.package_release_exists(package_name=package_name, version=version):
            self.warning(
                f'Trying to publish an existing release for package "{package_name}" version {version}'
            )
            if not force:
                return

        repository_token = self.search_app_or_suite_runtime_config(
            "pdm.repository.token", default=None
        ).get_str_or_none()

        repository_username = self.search_app_or_suite_runtime_config(
            "pdm.repository.username", default="__token__"
        ).get_str_or_none()

        self.subtitle("Publishing to PyPI")
        publish_cmd = ["pdm", "publish"]

        username = repository_username or "__token__"
        password = repository_token or self.get_env_parameter_or_suite_fallback(
            "PIPY_TOKEN"
        )

        if username:
            publish_cmd += ["--username", username]
        if password:
            publish_cmd += ["--password", password]

        shell_run(publish_cmd, inherit_stdio=True, cwd=self.get_path())

    def _wait_for_registry(self) -> None:
        import base64
        import urllib.error
        import urllib.request

        from wexample_helpers.helpers.polling_callback_manager import (
            PollingCallbackManager,
        )

        repository_url = self.search_app_or_suite_runtime_config(
            "pdm.repository.url", default=None
        ).get_str_or_none()
        if not repository_url:
            repository_url = "https://pypi.org"

        token = self.search_app_or_suite_runtime_config(
            "pdm.repository.token", default=None
        ).get_str_or_none()
        username = (
            self.search_app_or_suite_runtime_config(
                "pdm.repository.username", default="__token__"
            ).get_str_or_none()
            or "__token__"
        )

        package = self.get_package_name()
        version = self.get_setup_version()
        url = f"{repository_url.rstrip('/')}/simple/{package}/"

        def check_available() -> bool | None:
            try:
                req = urllib.request.Request(url)
                if token:
                    credentials = base64.b64encode(
                        f"{username}:{token}".encode()
                    ).decode()
                    req.add_header("Authorization", f"Basic {credentials}")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200 and version in resp.read().decode():
                        return True
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
            except Exception:
                pass
            return None

        max_attempts = 40
        delay_seconds = 30

        self.log(f"Waiting for {package}=={version} to appear on registry…")

        def on_retry(attempt, max_a, delay, _exc, _msg) -> None:
            self.log(
                f"Not yet available (attempt {attempt}/{max_a}), retrying in {delay}s…"
            )

        PollingCallbackManager(
            callback=check_available,
            max_attempts=max_attempts,
            delay_seconds_callback=lambda _attempt: delay_seconds,
            on_retry_callback=on_retry,
            timeout_message=(
                f"Timed out waiting for {package}=={version} on registry after "
                f"{max_attempts * delay_seconds // 60} minutes."
            ),
        ).run()

        self.success(f"{package}=={version} is available.")
