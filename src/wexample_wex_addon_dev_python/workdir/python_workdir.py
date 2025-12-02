from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from wexample_app.item.file.iml_file import ImlFile
from wexample_event.dataclass.event import Event
from wexample_event.dataclass.listener_record import EventCallback
from wexample_filestate.const.types_state_items import TargetFileOrDirectoryType
from wexample_filestate.item.file.json_file import JsonFile
from wexample_filestate.operation.abstract_operation import AbstractOperation
from wexample_filestate.operation.file_rename_operation import FileRenameOperation
from wexample_filestate_python.const.path import PATH_DIR_SRC, PATH_DIR_TESTS
from wexample_filestate_python.const.python_file import (
    PYTHON_FILE_EXTENSION,
    PYTHON_FILE_PYTEST_COVERAGE_JSON,
)
from wexample_wex_addon_app.workdir.code_base_workdir import (
    CodeBaseWorkdir,
)

from wexample_wex_addon_dev_python.const.python import (
    PYTHON_PYTEST_COV_FORMAT_HTML,
    PYTHON_PYTEST_COV_FORMAT_JSON,
    PYTHON_PYTEST_COV_REPORT_DIR,
)
from wexample_wex_addon_dev_python.file.python_app_iml_file import PythonAppImlFile

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

    from wexample_wex_addon_dev_python.file.python_pyproject_toml_file import (
        PythonPyprojectTomlFile,
    )


class PythonWorkdir(CodeBaseWorkdir):
    def app_install(self, env: str | None = None, force: bool = False) -> Path:
        from wexample_wex_addon_app.helpers.python import (
            python_ensure_pip_or_fail,
            python_install_environment,
        )

        # Check if a venv path is somewhere in the config hierarchy.
        venv_path_config = self.search_app_or_suite_runtime_config("python.venv_path")

        # There is no venv, so create a venv for this project.
        if venv_path_config.is_none():
            venv_path = python_install_environment(path=self.get_path())
        else:
            venv_path = Path(venv_path_config.get_str())

        self.log(f"Using venv: @path{{{venv_path}}}")
        python_ensure_pip_or_fail(venv_path)

        self._install_dependencies_in_venv(
            venv_path=venv_path,
            env=env,
            force=force,
        )

        # Use standard PDM install
        return venv_path

    def get_app_config_file(self, reload: bool = True) -> PythonPyprojectTomlFile:
        from wexample_wex_addon_dev_python.file.python_pyproject_toml_file import (
            PythonPyprojectTomlFile,
        )

        config_file = self.find_by_type(PythonPyprojectTomlFile)
        # Read once to populate content with file source.
        config_file.read_text(reload=reload)
        return config_file

    def get_dependencies_versions(self) -> dict[str, str]:
        return self.get_app_config_file().get_dependencies_versions()

    def get_main_code_file_extension(self) -> str:
        return PYTHON_FILE_EXTENSION

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

    def get_python_exec_module_command(self, module_name: str) -> list[str]:
        return [self.get_python_path(), "-m", module_name]

    def get_python_path(self) -> Path:
        return self.get_venv_bin_path() / "python"

    def get_venv_bin_path(self) -> Path:
        return self.get_venv_path() / "bin"

    def get_venv_path(self) -> Path:
        return self.get_path() / ".venv"

    def has_coverage_changes_since_last_report(self) -> bool:
        """Return True if coverage has changed since last saved report."""
        last_report = (
            self.app_workdir.get_config()
            .search("test.coverage.last_report")
            .get_dict_or_default()
        )

        if not last_report:
            return True

        current_coverage = self._run_coverage()

        return current_coverage != last_report.get("percent")

    def operation_add_event_listener(
        self,
        operation: AbstractOperation | type[AbstractOperation],
        callback: EventCallback,
        suffix: str | None = None,
        **kwargs,
    ) -> None:
        self.add_event_listener(
            name=operation.get_event_name(suffix=suffix), callback=callback, **kwargs
        )

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_config.config_value.callback_render_config_value import (
            CallbackRenderConfigValue,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate.option.children_filter_option import (
            ChildrenFilterOption,
        )
        from wexample_helpers.helpers.array import array_dict_get_by

        from wexample_wex_addon_dev_python.file.python_pyproject_toml_file import (
            PythonPyprojectTomlFile,
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
                    "class": PythonPyprojectTomlFile,
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

    def save_dependency(self, package_name: str, version: str) -> bool:
        """Add or update a dependency with strict version."""
        config = self.get_app_config_file()
        updated = config.add_dependency(package_name=package_name, version=version)

        if updated:
            config.write_parsed()

        return updated

    def save_project_config_file(self, config: StructuredData) -> None:
        """Save the project configuration to pyproject.toml."""
        config_file = self.get_app_config_file()
        config_file.write(config)

    def test_get_command(
        self, format: str = PYTHON_PYTEST_COV_FORMAT_JSON
    ) -> list[str]:
        cmd = self.get_python_exec_module_command("pytest")
        cmd.extend(
            [
                "--cov",
                f"--cov-report={format}",
            ]
        )

        return cmd

    def test_run(self, format: str = PYTHON_PYTEST_COV_FORMAT_JSON) -> None:
        self.shell_run_for_app(cmd=self.test_get_command(format=format))

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

        if format == PYTHON_PYTEST_COV_FORMAT_HTML:
            report_path = self.get_path() / PYTHON_PYTEST_COV_REPORT_DIR / "index.html"
            if report_path.exists():
                self.info(f"Report: @path{{{report_path}}}")

    def update_dependencies(self, dependencies_map: dict[str, str]) -> None:
        """Update dependencies versions based on the provided map.

        Args:
            dependencies_map: Dictionary mapping package names to their new versions.
                             Example: {"wexample-helpers": "0.2.3", "attrs": "23.1.0"}
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        config_file = self.get_app_config_file()

        # Canonicalize the keys in dependencies_map for consistent matching
        canonical_map = {
            canonicalize_name(name): version
            for name, version in dependencies_map.items()
        }

        # Get current dependencies
        current_deps = config_file.list_dependencies_names()

        # Update each dependency if it's in the map
        for dep_spec in current_deps:
            try:
                req = Requirement(dep_spec)
                canonical_name = canonicalize_name(req.name)

                # If this dependency is in our update map, update it
                if canonical_name in canonical_map:
                    new_version = canonical_map[canonical_name]
                    # Use add_dependency which handles removal of old version
                    config_file.add_dependency(
                        package_name=req.name, version=new_version
                    )
            except Exception:
                # Skip unparsable dependencies
                continue

        # Save the updated config
        config_file.write_parsed()

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
        from wexample_filestate_python.option.python.add_future_annotations_option import (
            AddFutureAnnotationsOption,
        )
        from wexample_filestate_python.option.python.add_return_types_option import (
            AddReturnTypesOption,
        )
        from wexample_filestate_python.option.python.fix_attrs_option import (
            FixAttrsOption,
        )
        from wexample_filestate_python.option.python.fix_blank_lines_option import (
            FixBlankLinesOption,
        )
        from wexample_filestate_python.option.python.format_option import FormatOption
        from wexample_filestate_python.option.python.fstringify_option import (
            FstringifyOption,
        )
        from wexample_filestate_python.option.python.modernize_typing_option import (
            ModernizeTypingOption,
        )
        from wexample_filestate_python.option.python.order_class_attributes_option import (
            OrderClassAttributesOption,
        )
        from wexample_filestate_python.option.python.order_class_docstring_option import (
            OrderClassDocstringOption,
        )
        from wexample_filestate_python.option.python.order_class_methods_option import (
            OrderClassMethodsOption,
        )
        from wexample_filestate_python.option.python.order_constants_option import (
            OrderConstantsOption,
        )
        from wexample_filestate_python.option.python.order_iterable_items_option import (
            OrderIterableItemsOption,
        )
        from wexample_filestate_python.option.python.order_main_guard_option import (
            OrderMainGuardOption,
        )
        from wexample_filestate_python.option.python.order_module_docstring_option import (
            OrderModuleDocstringOption,
        )
        from wexample_filestate_python.option.python.order_module_functions_option import (
            OrderModuleFunctionsOption,
        )
        from wexample_filestate_python.option.python.order_module_metadata_option import (
            OrderModuleMetadataOption,
        )
        from wexample_filestate_python.option.python.order_type_checking_block_option import (
            OrderTypeCheckingBlockOption,
        )
        from wexample_filestate_python.option.python.relocate_imports_option import (
            RelocateImportsOption,
        )
        from wexample_filestate_python.option.python.remove_unused_option import (
            RemoveUnusedOption,
        )
        from wexample_filestate_python.option.python.sort_imports_option import (
            SortImportsOption,
        )
        from wexample_filestate_python.option.python.unquote_annotations_option import (
            UnquoteAnnotationsOption,
        )

        return ChildrenFilterOption(
            pattern={
                "class": PythonFile,
                "type": DiskItemType.FILE,
                "python": {
                    # Configured for python >= 3.12
                    AddFutureAnnotationsOption.get_name(): True,
                    RelocateImportsOption.get_name(): True,
                    RemoveUnusedOption.get_name(): True,
                    SortImportsOption.get_name(): True,
                    ModernizeTypingOption.get_name(): True,
                    FstringifyOption.get_name(): True,
                    AddReturnTypesOption.get_name(): True,
                    UnquoteAnnotationsOption.get_name(): True,
                    FixAttrsOption.get_name(): True,
                    OrderTypeCheckingBlockOption.get_name(): True,
                    OrderModuleDocstringOption.get_name(): True,
                    OrderModuleMetadataOption.get_name(): True,
                    OrderConstantsOption.get_name(): True,
                    OrderIterableItemsOption.get_name(): True,
                    OrderModuleFunctionsOption.get_name(): True,
                    OrderMainGuardOption.get_name(): True,
                    OrderClassDocstringOption.get_name(): True,
                    OrderClassAttributesOption.get_name(): True,
                    OrderClassMethodsOption.get_name(): True,
                    FixBlankLinesOption.get_name(): True,
                    FormatOption.get_name(): True,
                },
            },
            name_pattern=r"^.*\.py$",
            recursive=True,
        )

    def _get_iml_file_class(self) -> type[ImlFile]:
        return PythonAppImlFile

    def _get_source_code_directories(self) -> [TargetFileOrDirectoryType]:
        src = self.find_by_name(PATH_DIR_SRC)

        if src:
            return [src]

        return []

    def _get_test_code_directories(self) -> [TargetFileOrDirectoryType]:
        tests = self.find_by_name(PATH_DIR_TESTS)

        if tests:
            return [tests]

        return []

    def _init_listeners(self) -> None:
        """Add event listeners"""
        self.operation_add_event_listener(
            operation=FileRenameOperation, suffix="post", callback=self._on_test_event
        )

    def _install_dependencies_in_venv(
        self, venv_path: Path, env: str | None = None, force: bool = False
    ) -> None:
        from wexample_wex_addon_app.helpers.python import (
            python_install_dependencies_in_venv,
        )

        toml_file = self.get_app_config_file()
        # Get all dependencies from pyproject.toml
        python_install_dependencies_in_venv(
            venv_path=venv_path, names=toml_file.list_dependencies_names()
        )

    def _on_test_event(self, event: Event) -> None:
        self.success("A python file has been renamed")
