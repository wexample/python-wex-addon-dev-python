from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.config_value.readme_content_config_value import (
    ReadmeContentConfigValue,
)
from wexample_helpers.classes.field import public_field
from wexample_helpers.decorator.base_class import base_class

if TYPE_CHECKING:
    from wexample_wex_addon_dev_python.workdir.python_package_workdir import (
        PythonPackageWorkdir,
    )


@base_class
class PythonPackageReadmeContentConfigValue(ReadmeContentConfigValue):
    workdir: PythonPackageWorkdir = public_field(
        description="The python package workdir"
    )

    def _get_bundled_templates_path(self):
        from pathlib import Path

        return Path(__file__).parent.parent / "resources" / "readme_templates"

    def _get_project_description(self) -> str:
        doc = self.workdir.get_project_config()
        project = doc.get("project", {}) if isinstance(doc, dict) else {}
        return project.get("description", "")

    def _get_project_homepage(self) -> str:
        doc = self.workdir.get_project_config()
        project = doc.get("project", {}) if isinstance(doc, dict) else {}
        urls = (
            project.get("urls", {}) if isinstance(project.get("urls", {}), dict) else {}
        )
        return urls.get("homepage") or urls.get("Homepage") or ""

    def _get_project_license(self) -> str:
        doc = self.workdir.get_project_config()
        project = doc.get("project", {}) if isinstance(doc, dict) else {}
        license_field = project.get("license", {})
        if isinstance(license_field, dict):
            return license_field.get("text", "") or license_field.get("file", "")
        return str(license_field) if license_field else ""

    # Python-specific context extension
    def _get_template_context(self) -> dict:
        # Get base context from parent
        context = super()._get_template_context()

        # Add Python-specific variables
        doc = self.workdir.get_project_config()
        project = doc.get("project", {}) if isinstance(doc, dict) else {}

        context["python_version"] = project.get("requires-python", "")
        context["workdir"] = self.workdir

        return context
