from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_config.const.types import DictConfig
from wexample_filestate.item.file.toml_file import TomlFile

if TYPE_CHECKING:
    from wexample_wex_addon_dev_python.workdir.python_packages_suite_workdir import PythonPackagesSuiteWorkdir


class PythonPackageTomlFile(TomlFile):
    def prepare_value(self, prepare_value: DictConfig | None = None) -> DictConfig:
        from wexample_wex_addon_dev_python.config_option.format_python_package_toml_option import (
            FormatPythonPackageTomlOption,
        )

        prepare_value[FormatPythonPackageTomlOption.get_snake_short_class_name()] = True

        return prepare_value

    def find_suite_workdir(self) -> PythonPackagesSuiteWorkdir | None:
        from wexample_wex_addon_dev_python.workdir.python_packages_suite_workdir import PythonPackagesSuiteWorkdir
        return self.find_closest(PythonPackagesSuiteWorkdir)
