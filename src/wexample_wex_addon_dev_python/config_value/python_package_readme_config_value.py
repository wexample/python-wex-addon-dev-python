from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.decorator.base_class import base_class
from wexample_wex_addon_app.config_value.app_readme_config_value import (
    AppReadmeConfigValue,
)

if TYPE_CHECKING:
    pass


@base_class
class PythonPackageReadmeContentConfigValue(AppReadmeConfigValue):
    """README generation for Python packages."""

    def _get_app_description(self) -> str:
        """Extract description from pyproject.toml."""
        return self.workdir.get_app_config().get("project", {}).get("description")

    def _get_app_homepage(self) -> str:
        """Extract homepage URL from pyproject.toml."""
        project = self.workdir.get_app_config()
        urls = (
            project.get("urls", {}) if isinstance(project.get("urls", {}), dict) else {}
        )
        return urls.get("homepage") or urls.get("Homepage") or ""

    def _get_project_license(self) -> str | None:
        """Extract license information from pyproject.toml."""
        project = self.workdir.get_app_config()
        license_field = project.get("license", {})
        if isinstance(license_field, dict):
            return license_field.get("text", "") or license_field.get("file", "")
        return str(license_field) if license_field else ""

    def _get_template_context(self) -> dict:
        """Build template context with Python-specific variables.

        Adds python_version to the base context.
        """
        context = super()._get_template_context()

        # Add Python-specific variable
        context["python_version"] = (
            self.workdir.get_app_config().get("project", {}).get("requires-python", "")
        )

        return context
