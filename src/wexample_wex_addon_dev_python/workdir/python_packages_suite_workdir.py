from __future__ import annotations

from pathlib import Path

from wexample_config.const.types import DictConfig
from wexample_wex_addon_app.workdir.framework_packages_suite_workdir import (
    FrameworkPackageSuiteWorkdir,
)
from wexample_wex_addon_dev_python.workdir.python_package_workdir import PythonPackageWorkdir


class PythonPackagesSuiteWorkdir(FrameworkPackageSuiteWorkdir):
    def publish_suite(self):
        # TODO
        for package in self.get_packages():
            self.io.log(f'Publishing package {package.get_project_name()}')

    def get_packages(self) -> list[PythonPackageWorkdir]:
        pip_dir = self.find_by_name(item_name='pip')
        if pip_dir:
            return pip_dir.get_children_list()
        return []

    def prepare_value(self, raw_value: DictConfig | None = None) -> DictConfig:
        from wexample_filestate.config_option.children_filter_config_option import (
            ChildrenFilterConfigOption,
        )
        from wexample_filestate.const.disk import DiskItemType
        from wexample_wex_addon_dev_python.workdir.python_package_workdir import (
            PythonPackageWorkdir,
        )

        raw_value = super().prepare_value(raw_value=raw_value)

        children = raw_value["children"]

        # By default, consider each sub folder as a pip package
        children.append(
            {
                "name": "pip",
                "type": DiskItemType.DIRECTORY,
                "children": [
                    ChildrenFilterConfigOption(
                        filter=self._has_pyproject,
                        pattern={
                            "class": PythonPackageWorkdir,
                            "type": DiskItemType.DIRECTORY,
                        },
                    )
                ],
            }
        )

        return raw_value

    def _has_pyproject(self, entry: Path) -> bool:
        return entry.is_dir() and (entry / "pyproject.toml").is_file()
