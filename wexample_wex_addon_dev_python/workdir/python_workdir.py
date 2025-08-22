from typing import TYPE_CHECKING, List, Optional, Type

from wexample_config.const.types import DictConfig
from wexample_config.options_provider.abstract_options_provider import (
    AbstractOptionsProvider,
)
from wexample_filestate_python.config_option.python_config_option import (
    PythonConfigOption,
)
from wexample_helpers.helpers.string import string_to_snake_case
from wexample_wex_addon_app.workdir.framework_package_workdir import (
    FrameworkPackageWorkdir,
)

if TYPE_CHECKING:
    from wexample_filestate.config_option.children_file_factory_config_option import (
        ChildrenFileFactoryConfigOption,
    )
    from wexample_filestate.config_option.mixin.item_config_option_mixin import (
        ItemTreeConfigOptionMixin,
    )
    from wexample_filestate.operations_provider.abstract_operations_provider import (
        AbstractOperationsProvider,
    )


class PythonWorkdir(FrameworkPackageWorkdir):
    def get_options_providers(self) -> list[type["AbstractOptionsProvider"]]:
        from wexample_filestate.options_provider.default_options_provider import (
            DefaultOptionsProvider,
        )
        from wexample_filestate_git.options_provider.git_options_provider import (
            GitOptionsProvider,
        )
        from wexample_filestate_python.options_provider.python_options_provider import (
            PythonOptionsProvider,
        )

        return [DefaultOptionsProvider, GitOptionsProvider, PythonOptionsProvider]

    def get_operations_providers(self) -> list[type["AbstractOperationsProvider"]]:
        from wexample_filestate.operations_provider.default_operations_provider import (
            DefaultOperationsProvider,
        )
        from wexample_filestate_git.operations_provider.git_operations_provider import (
            GitOperationsProvider,
        )
        from wexample_filestate_python.operations_provider.python_operations_provider import (
            PythonOperationsProvider,
        )

        return [
            DefaultOperationsProvider,
            GitOperationsProvider,
            PythonOperationsProvider,
        ]

    @staticmethod
    def _create_package_name_snake(option: "ItemTreeConfigOptionMixin") -> str:
        import os

        return "wexample_" + string_to_snake_case(
            os.path.basename(os.path.realpath(option.get_parent_item().get_path()))
        )

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_filestate.config_option.children_filter_config_option import (
            ChildrenFilterConfigOption,
        )
        from wexample_filestate.const.disk import DiskItemType

        raw_value = super().prepare_value(raw_value=raw_value)

        children = raw_value["children"]

        children.extend(
            [
                {
                    "name": ".gitignore",
                    "type": DiskItemType.FILE,
                    "should_exist": True,
                },
                {
                    "name": "requirements.in",
                    "type": DiskItemType.FILE,
                    "should_exist": True,
                },
                {
                    "name": "requirements.txt",
                    "type": DiskItemType.FILE,
                    "should_exist": True,
                },
                {
                    "name": "tests",
                    "type": DiskItemType.DIRECTORY,
                    "should_exist": True,
                    "children": [
                        self._create_init_children_factory(),
                        self._create_python_file_children_filter(),
                    ],
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
                ChildrenFilterConfigOption(
                    pattern={
                        "name_pattern": r"^.*\.egg-info$",
                        "type": DiskItemType.DIRECTORY,
                        "should_exist": False,
                    }
                ),
            ]
        )

        return raw_value

    def _create_python_file_children_filter(self) -> "ChildrenFileFactoryConfigOption":
        from wexample_filestate.config_option.children_filter_config_option import (
            ChildrenFilterConfigOption,
        )
        from wexample_filestate.const.disk import DiskItemType

        return ChildrenFilterConfigOption(
            pattern={
                "name_pattern": r"^.*\.py$",
                "type": DiskItemType.FILE,
                "python": [
                    PythonConfigOption.OPTION_NAME_MODERNIZE_TYPING,
                    PythonConfigOption.OPTION_NAME_FSTRINGIFY,
                    PythonConfigOption.OPTION_NAME_ADD_RETURN_TYPES,
                    PythonConfigOption.OPTION_NAME_SORT_IMPORTS,
                    PythonConfigOption.OPTION_NAME_FORMAT,
                ],
            },
            recursive=True,
        )

    def _create_init_children_factory(self) -> "ChildrenFileFactoryConfigOption":
        from wexample_filestate.config_option.children_file_factory_config_option import (
            ChildrenFileFactoryConfigOption,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate.const.globals import NAME_PATTERN_NO_LEADING_DOT
        from wexample_filestate_python.const.name_pattern import (
            NAME_PATTERN_PYTHON_NOT_PYCACHE,
        )

        return ChildrenFileFactoryConfigOption(
            pattern={
                "name": "__init__.py",
                "type": DiskItemType.FILE,
                "recursive": True,
                "name_pattern": [
                    NAME_PATTERN_PYTHON_NOT_PYCACHE,
                    NAME_PATTERN_NO_LEADING_DOT,
                ],
            }
        )
