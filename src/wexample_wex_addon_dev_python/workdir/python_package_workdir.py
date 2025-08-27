from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_config.const.types import DictConfig
from wexample_filestate.config_value.readme_content_config_value import (
    ReadmeContentConfigValue,
)
from wexample_helpers.const.types import StructuredData
from wexample_helpers.helpers.array import array_dict_get_by
from wexample_wex_addon_dev_python.file.python_package_toml_file import (
    PythonPackageTomlFile,
)
from wexample_wex_addon_dev_python.workdir.python_workdir import PythonWorkdir

if TYPE_CHECKING:
    from tomlkit import TOMLDocument
    from wexample_filestate.common.search_result import SearchResult


class PythonPackageWorkdir(PythonWorkdir):
    _project_info_cache = None

    def get_dependencies(self) -> list[str]:
        from packaging.requirements import Requirement

        dependencies = []
        for dependency in self.get_project_config_file().list_dependency_names():
            dependencies.append(Requirement(dependency).name)
        return dependencies

    def get_project_config_file(self, reload: bool = True) -> PythonPackageTomlFile:
        config_file = self.find_by_name("pyproject.toml")
        assert isinstance(config_file, PythonPackageTomlFile)
        # Read once to populate content with file source.
        config_file.read(reload=reload)
        return config_file

    def save_project_config_file(self, config: StructuredData) -> None:
        config_file = self.get_project_config_file()
        config_file.write(config)

    def get_project_config(self, reload: bool = True) -> TOMLDocument:
        """
        Fetch the data from the pyproject.toml file.
        """
        return self.get_project_config_file(reload=reload).content

    def get_package_name(self) -> str:
        from wexample_helpers.helpers.string import string_to_kebab_case

        return string_to_kebab_case(self.get_package_import_name())

    def get_package_import_name(self) -> str:
        # TODO concat suite name prefix.
        return f"wexample_{self.get_project_name()}"

    def depends_from(self, package: PythonPackageWorkdir) -> bool:
        for dependence_name in self.get_dependencies():
            if package.get_package_name() == dependence_name:
                return True
        return False

    def save_dependency(self, package: PythonPackageWorkdir) -> None:
        """Add a dependency, use strict version as this is the intended internal management."""
        config = self.get_project_config_file()
        config.add_dependency(
            f"{package.get_package_name()}=={package.get_project_version()}"
        )
        config.write()

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
        found = []
        from wexample_filestate.common.search_result import SearchResult
        from wexample_filestate_python.file.python_file import PythonFile

        def _search(item: PythonFile) -> None:
            found.extend(
                SearchResult.create_for_all_matches(
                    string, item, regex=regex, flags=flags
                )
            )

        self.for_each_child_of_type_recursive(callback=_search, class_type=PythonFile)

        return found

    def publish(self) -> None:
        from wexample_helpers.helpers.shell import shell_run

        # Map token to PyPI's token-based authentication if provided
        username = "__token__"
        password = self.get_env_parameter("PIPY_TOKEN")

        # Build the publish command, adding credentials only when given
        publish_cmd = ["pdm", "publish"]
        if username is not None:
            publish_cmd += ["--username", username]
        if password is not None:
            publish_cmd += ["--password", password]

        shell_run(
            publish_cmd,
            inherit_stdio=True,
        )

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_wex_addon_dev_python.config_option.format_python_package_toml_option import FormatPythonPackageTomlOption
        from wexample_config.config_value.callback_render_config_value import (
            CallbackRenderConfigValue,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_wex_addon_dev_python.file.python_package_toml_file import (
            PythonPackageTomlFile,
        )

        raw_value = super().prepare_value(raw_value=raw_value)

        # Retrieve the '.gitignore' configuration or create it if it doesn't exist
        config_gitignore = array_dict_get_by(
            "name", ".gitignore", raw_value["children"]
        )
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

        raw_value["children"].append(
            {
                "class": PythonPackageTomlFile,
                "name": "pyproject.toml",
                "type": DiskItemType.FILE,
                "should_exist": True,
            }
        )

        raw_value["children"].append(
            {
                "name": "src",
                "type": DiskItemType.DIRECTORY,
                "should_exist": True,
                "children": [
                    {
                        "name": CallbackRenderConfigValue(
                            raw=self._create_package_name_snake
                        ),
                        "type": DiskItemType.DIRECTORY,
                        "should_exist": True,
                        "children": [
                            self._create_init_children_factory(),
                            self._create_python_file_children_filter(),
                            {
                                "name": "py.typed",
                                "type": DiskItemType.FILE,
                                "should_exist": True,
                            },
                        ],
                    }
                ],
            }
        )

        return raw_value

    def _get_readme_content(self) -> ReadmeContentConfigValue | None:
        from wexample_wex_addon_dev_python.config_value.python_package_readme_config_value import (
            PythonPackageReadmeContentConfigValue,
        )

        return PythonPackageReadmeContentConfigValue(workdir=self)
