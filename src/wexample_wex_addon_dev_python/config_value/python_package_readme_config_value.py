from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.classes.field import public_field
from wexample_helpers.decorator.base_class import base_class
from wexample_wex_addon_app.config_value.app_readme_config_value import AppReadmeConfigValue

if TYPE_CHECKING:
    from wexample_wex_addon_dev_python.workdir.python_package_workdir import (
        PythonPackageWorkdir,
    )


@base_class
class PythonPackageReadmeContentConfigValue(AppReadmeConfigValue):
    """README generation for Python packages.
    
    Handles Python-specific metadata extraction from pyproject.toml.
    """

    workdir: PythonPackageWorkdir = public_field(
        description="The python package workdir"
    )

    def _get_bundled_templates_path(self):
        """Return path to bundled Python README templates."""
        from pathlib import Path

        return Path(__file__).parent.parent / "resources" / "readme_templates"

    def _get_project_config(self) -> dict:
        """Get the pyproject.toml configuration.
        
        Returns:
            The project configuration dictionary
        """
        doc = self.workdir.get_project_config()
        return doc.get("project", {}) if isinstance(doc, dict) else {}

    def _get_project_description(self) -> str:
        """Extract description from pyproject.toml."""
        return self._get_project_config().get("description", "")

    def _get_project_homepage(self) -> str:
        """Extract homepage URL from pyproject.toml."""
        project = self._get_project_config()
        urls = (
            project.get("urls", {}) if isinstance(project.get("urls", {}), dict) else {}
        )
        return urls.get("homepage") or urls.get("Homepage") or ""

    def _get_project_license(self) -> str:
        """Extract license information from pyproject.toml."""
        project = self._get_project_config()
        license_field = project.get("license", {})
        if isinstance(license_field, dict):
            return license_field.get("text", "") or license_field.get("file", "")
        return str(license_field) if license_field else ""

    def _get_project_dependencies(self) -> list[str]:
        """Extract dependencies from pyproject.toml."""
        return self._get_project_config().get("dependencies", [])

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
