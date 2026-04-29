from __future__ import annotations

from wexample_wex_addon_app.service.app_service import AppService as BaseAppService

PYPROJECT_TOML_CONTENT = """\
[build-system]
requires = ["pdm-backend"]
build-backend = "pdm.backend"

[project]
name = "app"
version = "0.0.1"
description = "Python app"
authors = [
    { name = "weeger", email = "contact@wexample.com" },
]
requires-python = ">=3.11,<3.14"
dependencies = [
]

[tool.pdm]
distribution = true

[tool.pdm.build]
package-dir = "src"

[[tool.pdm.build.packages]]
include = "app"
from = "src"

[tool.pdm.dev-dependencies]
dev = [
    "pytest>=8.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
"""

MAIN_CONTENT = """\
if __name__ == "__main__":
    print("OK")
"""


class AppService(BaseAppService):
    def get_workdir_contribution(self) -> dict:
        from wexample_filestate.const.disk import DiskItemType

        return {
            "children": [
                {
                    "name": "pyproject.toml",
                    "type": DiskItemType.FILE,
                    "should_exist": True,
                    "default_content": PYPROJECT_TOML_CONTENT,
                },
                {
                    "name": "src",
                    "type": DiskItemType.DIRECTORY,
                    "should_exist": True,
                    "children": [
                        {
                            "name": "app",
                            "type": DiskItemType.DIRECTORY,
                            "should_exist": True,
                            "children": [
                                {
                                    "name": "__init__.py",
                                    "type": DiskItemType.FILE,
                                    "should_exist": True,
                                },
                                {
                                    "name": "__main__.py",
                                    "type": DiskItemType.FILE,
                                    "should_exist": True,
                                    "default_content": MAIN_CONTENT,
                                },
                            ],
                        }
                    ],
                },
            ]
        }
