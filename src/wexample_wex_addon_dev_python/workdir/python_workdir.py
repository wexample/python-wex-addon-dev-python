from __future__ import annotations

from typing import TYPE_CHECKING
from wexample_wex_core.workdir.code_base_workdir import (
    CodeBaseWorkdir,
)

if TYPE_CHECKING:
    from wexample_config.const.types import DictConfig
    from wexample_config.options_provider.abstract_options_provider import (
        AbstractOptionsProvider,
    )
    from wexample_filestate.option.children_file_factory_option import (
        ChildrenFileFactoryOption,
    )
    from wexample_filestate.config_option.mixin.item_config_option_mixin import (
        ItemTreeConfigOptionMixin,
    )
    from wexample_filestate.operations_provider.abstract_operations_provider import (
        AbstractOperationsProvider,
    )


class PythonWorkdir(CodeBaseWorkdir):
    def get_dependencies(self) -> list[str]:
        from packaging.requirements import Requirement

        dependencies = []
        for dependency in self.get_project_config_file().list_dependency_names():
            dependencies.append(Requirement(dependency).name)
        return dependencies

    def get_operations_providers(self) -> list[type[AbstractOperationsProvider]]:
        from wexample_filestate_python.operations_provider.python_operations_provider import (
            PythonOperationsProvider,
        )

        operations = super().get_operations_providers()

        operations.extend(
            [
                PythonOperationsProvider,
            ]
        )

        return operations

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
        # TODO concat suite name prefix.
        return f"wexample_{self.get_project_name()}"

    def get_package_name(self) -> str:
        from wexample_helpers.helpers.string import string_to_kebab_case

        return string_to_kebab_case(self.get_package_import_name())

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_config.config_value.callback_render_config_value import (
            CallbackRenderConfigValue,
        )
        from wexample_filestate.option.children_filter_option import (
            ChildrenFilterOption,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_helpers.helpers.array import array_dict_get_by

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
        from wexample_filestate.option.children_file_factory_option import (
            ChildrenFileFactoryOption,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate.const.globals import NAME_PATTERN_NO_LEADING_DOT
        from wexample_filestate_python.const.name_pattern import (
            NAME_PATTERN_PYTHON_NOT_PYCACHE,
        )
        from wexample_filestate_python.file.python_file import PythonFile

        return ChildrenFileFactoryOption(
            pattern={
                "class": PythonFile,
                "name": "__init__.py",
                "type": DiskItemType.FILE,
                "name_pattern": [
                    NAME_PATTERN_PYTHON_NOT_PYCACHE,
                    NAME_PATTERN_NO_LEADING_DOT,
                ],
            },
            recursive=True,
        )

    def _create_package_name_snake(self, option: ItemTreeConfigOptionMixin) -> str:
        import os

        from wexample_helpers.helpers.string import string_to_snake_case

        # TODO make generic
        return "wexample_" + string_to_snake_case(
            os.path.basename(
                os.path.dirname(os.path.realpath(option.get_parent_item().get_path()))
            )
        )

    def _create_python_file_children_filter(self) -> ChildrenFileFactoryOption:
        from wexample_filestate.option.children_filter_option import ChildrenFilterOption
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate_python.file.python_file import PythonFile
        from wexample_filestate_python.option.python_option import PythonOption

        return ChildrenFilterOption(
            pattern={
                "class": PythonFile,
                "name_pattern": r"^.*\.py$",
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
            recursive=True,
        )
