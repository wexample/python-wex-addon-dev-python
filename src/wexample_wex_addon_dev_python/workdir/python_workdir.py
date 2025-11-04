from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tomlkit import TOMLDocument

from wexample_filestate.item.file.json_file import JsonFile
from wexample_filestate_python.const.python_file import PYTHON_FILE_PYTEST_COVERAGE_JSON
from wexample_wex_addon_app.helpers.python import python_install_environment
from wexample_wex_addon_app.workdir.code_base_workdir import (
    CodeBaseWorkdir,
)

if TYPE_CHECKING:
    from wexample_config.const.types import DictConfig
    from wexample_config.options_provider.abstract_options_provider import (
        AbstractOptionsProvider,
    )
    from wexample_filestate.config_option.mixin.item_config_option_mixin import (
        ItemTreeConfigOptionMixin,
    )
    from wexample_filestate.option.children_file_factory_option import (
        ChildrenFileFactoryOption,
    )
    from wexample_helpers.const.types import StructuredData
    from wexample_wex_addon_dev_python.file.python_package_toml_file import (
        PythonPackageTomlFile,
    )


class PythonWorkdir(CodeBaseWorkdir):
    def get_venv_path(self) -> Path:
        return self.get_path() / ".venv"

    def get_venv_bin_path(self) -> Path:
        return self.get_venv_path() / "bin"

    def get_python_path(self) -> Path:
        return self.get_venv_bin_path() / "python"

    def get_python_exec_module_command(self, module_name: str) -> list[str]:
        return [self.get_python_path(), "-m", module_name]

    def test_run(self) -> None:
        self.shell_run_for_app(cmd=self.test_get_command())

        json_file = JsonFile.create_from_path(
            path=self.get_path() / PYTHON_FILE_PYTEST_COVERAGE_JSON
        )
        totals = json_file.read_config().search("totals", default={}).get_dict()

        config_file = self.get_config_file()
        config = config_file.read_config()
        config.set_by_path(
            "test.coverage.last_report",
            {
                "covered": totals.get("covered_lines", 0),
                "excluded": totals.get("excluded_lines", 0),
                "missing": totals.get("missing_lines", 0),
                "percent": totals.get("percent_covered", 0),
                "total": totals.get("num_statements", 0),
            },
        )
        config_file.write_config()

    def test_get_command(self) -> list[str]:
        cmd = self.get_python_exec_module_command("pytest")
        cmd.extend(
            [
                "--cov",
                "--cov-report=json",
            ]
        )

        return cmd

    def app_install(self, env: str | None = None, force: bool = False) -> bool:
        # Use standard PDM install
        return python_install_environment(path=self.get_path())

    def get_dependencies(self) -> list[str]:
        from packaging.requirements import Requirement

        dependencies = []
        for dependency in self.get_project_config_file().list_dependency_names():
            dependencies.append(Requirement(dependency).name)
        return dependencies

    def get_options_providers(self) -> list[type[AbstractOptionsProvider]]:
        from wexample_filestate_python.options_provider.python_options_provider import (
            PythonOptionsProvider,
        )

        options = super().get_options_providers()

        options.extend(
            [
                PythonOptionsProvider,
            ]
        )

        return options

    def get_package_import_name(self) -> str:
        """Get the full package import name with vendor prefix."""
        return f"{self.get_vendor_name()}_{self.get_project_name()}"

    def get_package_name(self) -> str:
        from wexample_helpers.helpers.string import string_to_kebab_case

        return string_to_kebab_case(self.get_package_import_name())

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_config.config_value.callback_render_config_value import (
            CallbackRenderConfigValue,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate.option.children_filter_option import (
            ChildrenFilterOption,
        )
        from wexample_helpers.helpers.array import array_dict_get_by
        from wexample_wex_addon_dev_python.file.python_package_toml_file import (
            PythonPackageTomlFile,
        )

        raw_value = super().prepare_value(raw_value=raw_value)

        children = raw_value["children"]

        # Add rules to .gitignore
        array_dict_get_by("name", ".gitignore", raw_value["children"]).setdefault(
            "should_contain_lines", []
        ).extend(
            [
                ".pdm-python",
                ".python-version",
                ".venv",
                f"/{PYTHON_FILE_PYTEST_COVERAGE_JSON}",
            ]
        )

        children.extend(
            [
                {
                    "name": "tests",
                    "type": DiskItemType.DIRECTORY,
                    "should_exist": True,
                    "children": [
                        self._create_init_children_factory(),
                        self._create_python_file_children_filter(),
                    ],
                },
                {
                    "name": ".venv",
                    "type": DiskItemType.DIRECTORY,
                    "should_exist": True,
                },
                # Replaced by pdm
                {
                    "name": "requirements.in",
                    "type": DiskItemType.FILE,
                    "should_exist": False,
                },
                {
                    "name": "requirements.txt",
                    "type": DiskItemType.FILE,
                    "should_exist": False,
                },
                {
                    "name": "requirements-dev.in",
                    "type": DiskItemType.FILE,
                    "should_exist": False,
                },
                {
                    "name": "requirements-dev.txt",
                    "type": DiskItemType.FILE,
                    "should_exist": False,
                },
                # Pdm versions
                {
                    "class": PythonPackageTomlFile,
                    "name": "pyproject.toml",
                    "type": DiskItemType.FILE,
                    "should_exist": True,
                },
                # Remove unwanted files
                # Should only be created during deployment
                {
                    "name": "build",
                    "type": DiskItemType.DIRECTORY,
                    "should_exist": False,
                },
                {
                    "name": "dist",
                    "type": DiskItemType.DIRECTORY,
                    "should_exist": False,
                },
                ChildrenFilterOption(
                    pattern={
                        "name_pattern": r"^.*\.egg-info$",
                        "type": DiskItemType.DIRECTORY,
                        "should_exist": False,
                    }
                ),
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
                },
            ]
        )

        return raw_value

    def _create_init_children_factory(self) -> ChildrenFileFactoryOption:
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate.const.globals import NAME_PATTERN_NO_LEADING_DOT
        from wexample_filestate.option.children_file_factory_option import (
            ChildrenFileFactoryOption,
        )
        from wexample_filestate_python.const.name_pattern import (
            NAME_PATTERN_PYTHON_NOT_PYCACHE,
        )
        from wexample_filestate_python.file.python_file import PythonFile

        return ChildrenFileFactoryOption(
            pattern={
                "class": PythonFile,
                "name": "__init__.py",
                "type": DiskItemType.FILE,
            },
            name_pattern=[
                NAME_PATTERN_PYTHON_NOT_PYCACHE,
                NAME_PATTERN_NO_LEADING_DOT,
            ],
            recursive=True,
        )

    def _create_package_name_snake(self, option: ItemTreeConfigOptionMixin) -> str:
        import os

        from wexample_helpers.helpers.string import string_to_snake_case

        vendor_prefix = self.get_vendor_name()
        return (
            vendor_prefix
            + "_"
            + string_to_snake_case(
                os.path.basename(
                    os.path.dirname(
                        os.path.realpath(option.get_parent_item().get_path())
                    )
                )
            )
        )

    def _create_python_file_children_filter(self) -> ChildrenFileFactoryOption:
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate.option.children_filter_option import (
            ChildrenFilterOption,
        )
        from wexample_filestate_python.file.python_file import PythonFile
        from wexample_filestate_python.option.python_option import PythonOption

        return ChildrenFilterOption(
            pattern={
                "class": PythonFile,
                "type": DiskItemType.FILE,
                "python": {
                    # Configured for python >= 3.12
                    PythonOption.OPTION_NAME_ADD_FUTURE_ANNOTATIONS: True,
                    PythonOption.OPTION_NAME_RELOCATE_IMPORTS: True,
                    PythonOption.OPTION_NAME_REMOVE_UNUSED: True,
                    PythonOption.OPTION_NAME_SORT_IMPORTS: True,
                    PythonOption.OPTION_NAME_MODERNIZE_TYPING: True,
                    PythonOption.OPTION_NAME_FSTRINGIFY: True,
                    PythonOption.OPTION_NAME_ADD_RETURN_TYPES: True,
                    PythonOption.OPTION_NAME_UNQUOTE_ANNOTATIONS: True,
                    PythonOption.OPTION_NAME_FIX_ATTRS: True,
                    PythonOption.OPTION_NAME_ORDER_TYPE_CHECKING_BLOCK: True,
                    PythonOption.OPTION_NAME_ORDER_MODULE_DOCSTRING: True,
                    PythonOption.OPTION_NAME_ORDER_MODULE_METADATA: True,
                    PythonOption.OPTION_NAME_ORDER_CONSTANTS: True,
                    PythonOption.OPTION_NAME_ORDER_ITERABLE_ITEMS: True,
                    PythonOption.OPTION_NAME_ORDER_MODULE_FUNCTIONS: True,
                    PythonOption.OPTION_NAME_ORDER_MAIN_GUARD: True,
                    PythonOption.OPTION_NAME_ORDER_CLASS_DOCSTRING: True,
                    PythonOption.OPTION_NAME_ORDER_CLASS_ATTRIBUTES: True,
                    PythonOption.OPTION_NAME_ORDER_CLASS_METHODS: True,
                    PythonOption.OPTION_NAME_FIX_BLANK_LINES: True,
                    PythonOption.OPTION_NAME_FORMAT: True,
                },
            },
            name_pattern=r"^.*\.py$",
            recursive=True,
        )

    def get_project_config_file(self, reload: bool = True) -> PythonPackageTomlFile:
        from wexample_wex_addon_dev_python.file.python_package_toml_file import (
            PythonPackageTomlFile,
        )

        config_file = self.find_by_name("pyproject.toml")
        assert isinstance(config_file, PythonPackageTomlFile)
        # Read once to populate content with file source.
        config_file.read_text(reload=reload)
        return config_file

    def get_project_config(self, reload: bool = True) -> TOMLDocument:
        """
        Fetch the data from the pyproject.toml file.
        """
        return self.get_project_config_file(reload=reload).read_parsed()

    def save_dependency(self, package_name: str, version: str) -> None:
        """Add or update a dependency with strict version."""
        config = self.get_project_config_file()
        config.add_dependency(f"{package_name}=={version}")
        config.write_parsed()

    def save_project_config_file(self, config: StructuredData) -> None:
        """Save the project configuration to pyproject.toml."""
        config_file = self.get_project_config_file()
        config_file.write(config)

    def update_dependencies(self, dependencies_map: dict[str, str]) -> None:
        """Update dependencies versions based on the provided map.

        Args:
            dependencies_map: Dictionary mapping package names to their new versions.
                             Example: {"wexample-helpers": "0.2.3", "attrs": "23.1.0"}
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        config_file = self.get_project_config_file()

        # Canonicalize the keys in dependencies_map for consistent matching
        canonical_map = {
            canonicalize_name(name): version
            for name, version in dependencies_map.items()
        }

        # Get current dependencies
        current_deps = config_file.list_dependencies()

        # Update each dependency if it's in the map
        for dep_spec in current_deps:
            try:
                req = Requirement(dep_spec)
                canonical_name = canonicalize_name(req.name)

                # If this dependency is in our update map, update it
                if canonical_name in canonical_map:
                    new_version = canonical_map[canonical_name]
                    # Use add_dependency which handles removal of old version
                    config_file.add_dependency(f"{req.name}=={new_version}")
            except Exception:
                # Skip unparsable dependencies
                continue

        # Save the updated config
        config_file.write_parsed()
