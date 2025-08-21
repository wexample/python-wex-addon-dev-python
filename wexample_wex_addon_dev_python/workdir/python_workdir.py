from typing import Optional, List, Type, TYPE_CHECKING

from wexample_config.const.types import DictConfig
from wexample_config.options_provider.abstract_options_provider import AbstractOptionsProvider
from wexample_filestate.config_option.children_filter_config_option import ChildrenFilterConfigOption
from wexample_wex_addon_app.workdir.framework_package_workdir import FrameworkPackageWorkdir
from wexample_helpers.helpers.string import string_to_snake_case

if TYPE_CHECKING:
    from wexample_filestate.operations_provider.abstract_operations_provider import AbstractOperationsProvider
    from wexample_filestate.config_option.mixin.item_config_option_mixin import ItemTreeConfigOptionMixin


class PythonWorkdir(FrameworkPackageWorkdir):
    def get_options_providers(self) -> List[Type["AbstractOptionsProvider"]]:
        from wexample_filestate.options_provider.default_options_provider import DefaultOptionsProvider
        from wexample_filestate_git.options_provider.git_options_provider import GitOptionsProvider

        return [
            DefaultOptionsProvider,
            GitOptionsProvider
        ]

    def get_operations_providers(self) -> List[Type["AbstractOperationsProvider"]]:
        from wexample_filestate.operations_provider.default_operations_provider import DefaultOperationsProvider
        from wexample_filestate_git.operations_provider.git_operations_provider import GitOperationsProvider

        return [
            DefaultOperationsProvider,
            GitOperationsProvider
        ]

    @staticmethod
    def _create_package_name_snake(option: "ItemTreeConfigOptionMixin") -> str:
        import os
        return "wexample_" + string_to_snake_case(
            os.path.basename(os.path.realpath(option.get_parent_item().get_path())))

    def prepare_value(self, config: Optional[DictConfig] = None) -> DictConfig:
        from wexample_filestate.const.disk import DiskItemType

        config = super().prepare_value(config)

        config['children'] += [
            {
                'name': '.gitignore',
                'type': DiskItemType.FILE,
                'should_exist': True,
            },
            {
                'name': 'requirements.in',
                'type': DiskItemType.FILE,
                'should_exist': True,
            },
            {
                'name': 'requirements.txt',
                'type': DiskItemType.FILE,
                'should_exist': True,
            },
            {
                'name': 'tests',
                'type': DiskItemType.DIRECTORY,
                'should_exist': True,
            },
            # Remove unwanted files
            # Should only be created during deployment
            {
                'name': 'build',
                'type': DiskItemType.DIRECTORY,
                'should_exist': False,
            },
            {
                'name': 'dist',
                'type': DiskItemType.DIRECTORY,
                'should_exist': False,
            },
            ChildrenFilterConfigOption(pattern={
                'name_pattern': r'^.*\.egg-info$',
                'type': DiskItemType.DIRECTORY,
                'should_exist': False,
            }),
        ]

        return config
