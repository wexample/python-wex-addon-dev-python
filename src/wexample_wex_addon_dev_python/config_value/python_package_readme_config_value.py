from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class
from wexample_wex_addon_app.config_value.app_readme_config_value import AppReadmeConfigValue

if TYPE_CHECKING:
    pass


@base_class
class PythonPackageReadmeContentConfigValue(AppReadmeConfigValue):
    """README generation for Python packages."""

    def _get_template_context(self) -> dict:
        """Build template context with Python-specific variables.
        
        Adds python_version to the base context.
        """
        context = super()._get_template_context()

        # Add Python-specific variable
        context["python_version"] = self._get_project_config().get(
            "requires-python", ""
        )

        return context
