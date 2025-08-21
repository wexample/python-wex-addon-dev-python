from typing import Optional, TYPE_CHECKING

from wexample_config.const.types import DictConfig
from wexample_helpers.helpers.array import array_dict_get_by
from wexample_wex_addon_dev_python.workdir.python_workdir import PythonWorkdir


class PythonPackageWorkdir(PythonWorkdir):
    _project_info_cache = None

    def get_project_info(self, force: bool = False, default: dict = {}) -> dict:
        """
        Fetch the data from the pyproject.toml file.
        """
        # Return cached data if available and force is False
        if not force and self._project_info_cache is not None:
            return self._project_info_cache

        from wexample_helpers.helpers.file import file_read
        import tomli

        project_path = self.get_resolved()
        pyproject_file = f"{project_path}pyproject.toml"

        # Read the pyproject.toml file
        try:
            pyproject_content = file_read(pyproject_file)
            pyproject_data = tomli.loads(pyproject_content)
            # Store in cache
            self._project_info_cache = pyproject_data
        except FileNotFoundError:
            return default

        return pyproject_data

    def prepare_value(self, config: Optional[DictConfig] = None) -> DictConfig:
        from wexample_filestate.const.disk import DiskItemType
        from wexample_config.config_value.callback_render_config_value import CallbackRenderConfigValue

        config = super().prepare_value(config)

        # Retrieve the '.gitignore' configuration or create it if it doesn't exist
        config_gitignore = array_dict_get_by('name', '.gitignore', config["children"])
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

            should_contain_lines = config_gitignore.setdefault("should_contain_lines", [])
            if not isinstance(should_contain_lines, list):
                raise ValueError("'should_contain_lines' must be a list")

            for category, rules in generic_gitignore_rules.items():
                category_header = f"# {category}"
                if category_header not in should_contain_lines:
                    should_contain_lines.append(category_header)

                for rule in rules:
                    if rule not in should_contain_lines:
                        should_contain_lines.append(rule)

        config["children"].append(
            {
                'name': 'pyproject.toml',
                'type': DiskItemType.FILE,
                'should_exist': True,
            }
        )

        config["children"].append(
            {
                'name': CallbackRenderConfigValue(raw=self._create_package_name_snake),
                'type': DiskItemType.DIRECTORY,
                'should_exist': True,
                "children": [
                    self._create_init_children_factory(),
                    self._create_python_file_children_filter(),
                ]
            }
        )

        return config
