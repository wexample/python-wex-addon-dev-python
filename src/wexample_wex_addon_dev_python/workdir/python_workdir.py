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
    from wexample_filestate.config_option.children_file_factory_config_option import (
        ChildrenFileFactoryConfigOption,
    )
    from wexample_filestate.config_option.mixin.item_config_option_mixin import (
        ItemTreeConfigOptionMixin,
    )
    from wexample_filestate.operations_provider.abstract_operations_provider import (
        AbstractOperationsProvider,
    )


class PythonWorkdir(CodeBaseWorkdir):
    def get_package_import_name(self) -> str:
        # TODO concat suite name prefix.
        return f"wexample_{self.get_project_name()}"

    def get_package_name(self) -> str:
        from wexample_helpers.helpers.string import string_to_kebab_case

        return string_to_kebab_case(self.get_package_import_name())

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

    def _create_package_name_snake(self, option: ItemTreeConfigOptionMixin) -> str:
        import os

        from wexample_helpers.helpers.string import string_to_snake_case

        # TODO make generic
        return "wexample_" + string_to_snake_case(
            os.path.basename(
                os.path.dirname(os.path.realpath(option.get_parent_item().get_path()))
            )
        )

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_config.config_value.callback_render_config_value import (
            CallbackRenderConfigValue,
        )
        from wexample_filestate.config_option.children_filter_config_option import (
            ChildrenFilterConfigOption,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_helpers.helpers.array import array_dict_get_by

        raw_value = super().prepare_value(raw_value=raw_value)

        children = raw_value["children"]

        # Add rules to .gitignore
        array_dict_get_by("name", ".gitignore", raw_value["children"]).setdefault(
            "should_contain_lines", []
        ).extend([".pdm-python", ".python-version", ".venv"])

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
                ChildrenFilterConfigOption(
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

    def _create_python_file_children_filter(self) -> ChildrenFileFactoryConfigOption:
        from wexample_filestate.config_option.children_filter_config_option import (
            ChildrenFilterConfigOption,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate_python.config_option.python_config_option import (
            PythonConfigOption,
        )
        from wexample_filestate_python.file.python_file import PythonFile

        return ChildrenFilterConfigOption(
            pattern={
                "class": PythonFile,
                "name_pattern": r"^.*\.py$",
                "type": DiskItemType.FILE,
                "python": [
                    # Configured for python >= 3.12
                    # filestate: python-iter able-sort
                    # PythonConfigOption.OPTION_NAME_ADD_FUTURE_ANNOTATIONS,
                    # PythonConfigOption.OPTION_NAME_REMOVE_UNUSED,
                    # PythonConfigOption.OPTION_NAME_RELOCATE_IMPORTS,
                    # PythonConfigOption.OPTION_NAME_SORT_IMPORTS,
                    # PythonConfigOption.OPTION_NAME_MODERNIZE_TYPING,
                    # PythonConfigOption.OPTION_NAME_FSTRINGIFY,
                    # PythonConfigOption.OPTION_NAME_ADD_RETURN_TYPES,
                    # PythonConfigOption.OPTION_NAME_UNQUOTE_ANNOTATIONS,
                    # PythonConfigOption.OPTION_NAME_FORMAT,
                    # PythonConfigOption.OPTION_NAME_ORDER_TYPE_CHECKING_BLOCK,
                    # PythonConfigOption.OPTION_NAME_ORDER_MODULE_DOCSTRING,
                    # PythonConfigOption.OPTION_NAME_ORDER_MODULE_METADATA,
                    # PythonConfigOption.OPTION_NAME_ORDER_CONSTANTS,
                    # PythonConfigOption.OPTION_NAME_ORDER_ITERABLE_ITEMS,
                    # PythonConfigOption.OPTION_NAME_ORDER_MODULE_FUNCTIONS,

                    # CLASS-LEVEL REORDERING:
                    # 11. Preserve class header, decorators, and docstring at top
                    # 12. Sort class attributes: special ones first (__slots__, __match_args__, Config),
                    #     then public A-Z, then private/protected A-Z
                    # 13. Order special methods (__dunder__) in logical sequence:
                    #     - Construction: __new__, __init__
                    #     - Representation: __repr__, __str__
                    #     - Comparison/hash: __lt__, __le__, __eq__, __ne__, __gt__, __ge__, __hash__
                    #     - Truthiness: __bool__
                    #     - Attribute access: __getattribute__, __getattr__, __setattr__, __delattr__
                    #     - Container/iteration: __len__, __iter__, __getitem__, __setitem__, __delitem__
                    #     - Callable: __call__
                    #     - Context managers: __enter__, __exit__, __aenter__, __aexit__
                    #     - Async protocols: __await__, __aiter__, __anext__
                    #     - Descriptors/pickling: __get__, __set__, __delete__, __getstate__, __setstate__
                    # 14. Sort class methods (@classmethod): public A-Z, then private A-Z
                    # 15. Sort static methods (@staticmethod): public A-Z, then private A-Z
                    # 16. Group properties by name (getter + setter + deleter together), sort groups A-Z
                    # 17. Sort instance methods: public A-Z, then private/protected A-Z
                    # 18. Sort nested classes A-Z by name
                    #
                    # PRESERVATION RULES:
                    # 19. Never split @overload series from their implementation
                    # 20. Keep property getter/setter/deleter groups together
                    # 21. Preserve Enum member order (may be semantically relevant)
                    # 22. Preserve dataclass field order (affects __init__ generation)
                    # 23. Handle async variants to follow their sync counterparts
                    # 24. Use case-insensitive A-Z sorting with _ after letters: a < b < z < _a < __a
                    # 25. Preserve all docstrings for modules, classes, functions, and methods
                ],
            },
            recursive=True,
        )

    def _create_init_children_factory(self) -> ChildrenFileFactoryConfigOption:
        from wexample_filestate.config_option.children_file_factory_config_option import (
            ChildrenFileFactoryConfigOption,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_filestate.const.globals import NAME_PATTERN_NO_LEADING_DOT
        from wexample_filestate_python.const.name_pattern import (
            NAME_PATTERN_PYTHON_NOT_PYCACHE,
        )
        from wexample_filestate_python.file.python_file import PythonFile

        return ChildrenFileFactoryConfigOption(
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
