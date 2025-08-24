from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_config.const.types import DictConfig
from wexample_helpers.helpers.array import array_dict_get_by
from wexample_wex_addon_dev_python.workdir.python_workdir import PythonWorkdir

if TYPE_CHECKING:
    from wexample_config.config_value.nested_config_value import NestedConfigValue


class PythonPackageWorkdir(PythonWorkdir):
    _project_info_cache = None

    def get_dependencies(self) -> list[str]:
        from packaging.requirements import Requirement
        dependencies = []
        info = self.get_project_info()
        for dependency in info.search('project.dependencies').get_list():
            dependencies.append(Requirement(dependency.get_str()).name)
        return dependencies

    def get_project_info(self, force: bool = False, default: dict | None = None) -> NestedConfigValue:
        from wexample_config.config_value.nested_config_value import NestedConfigValue

        """
        Fetch the data from the pyproject.toml file.
        """
        # Return cached data if available and force is False
        if not force and self._project_info_cache is not None:
            return self._project_info_cache

        import tomli
        from wexample_helpers.helpers.file import file_read

        project_path = self.get_resolved()
        pyproject_file = f"{project_path}pyproject.toml"

        # Read the pyproject.toml file
        try:
            pyproject_content = file_read(pyproject_file)
            pyproject_data = tomli.loads(pyproject_content)
            # Store in cache
            self._project_info_cache = NestedConfigValue(raw=pyproject_data)
        except FileNotFoundError:
            return NestedConfigValue(raw=default or {})

        return self._project_info_cache

    def get_package_name(self) -> str:
        return f"wexample_{self.get_project_name()}"

    def publish(self):
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

    def prepare_value(self, prepare_value: DictConfig | None = None) -> DictConfig:
        from wexample_config.config_value.callback_render_config_value import (
            CallbackRenderConfigValue,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_wex_addon_dev_python.file.python_package_toml_file import (
            PythonPackageTomlFile,
        )

        prepare_value = super().prepare_value(prepare_value)

        # Retrieve the '.gitignore' configuration or create it if it doesn't exist
        config_gitignore = array_dict_get_by(
            "name", ".gitignore", prepare_value["children"]
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

        prepare_value["children"].append(
            {
                "class": PythonPackageTomlFile,
                "name": "pyproject.toml",
                "type": DiskItemType.FILE,
                "should_exist": True,
            }
        )

        prepare_value["children"].append(
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

        return prepare_value
