from __future__ import annotations

from typing import Any, ClassVar

from wexample_config.config_option.abstract_config_option import AbstractConfigOption


class FormatPythonPackageTomlOption(AbstractConfigOption):
    """Enable formatting of pyproject.toml for Python packages."""

    OPTION_NAME: ClassVar[str] = "format_python_package_toml"

    @staticmethod
    def get_raw_value_allowed_type() -> Any:
        # Simple boolean toggle for enabling the operation
        return bool
