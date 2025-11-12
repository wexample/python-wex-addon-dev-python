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

    def get_templates(self) -> list[str] | None:
        # Prepare context for Jinja2 rendering
        context = self._get_template_context()

        # Define fixed order of README sections
        section_names = [
            "title",
            "table-of-contents",
            "status-compatibility",
            "prerequisites",
            "installation",
            "quickstart",
            "basic-usage",
            "configuration",
            "logging",
            "api-reference",
            "examples",
            "tests",
            "code-quality",
            "versioning",
            "changelog",
            "migration-notes",
            "roadmap",
            "troubleshooting",
            "security",
            "privacy",
            "support",
            "contribution-guidelines",
            "maintainers",
            "license",
            "useful-links",
            "suite-integration",
            "compatibility-matrix",
            "requirements",
            "dependencies",
            "links",
            "suite-signature",
        ]

        # First pass: collect available sections (excluding title and table-of-contents)
        available_sections = []
        for section_name in section_names:
            if section_name not in ["title", "table-of-contents"]:
                # Check if section exists
                if self._section_exists(section_name):
                    available_sections.append(
                        {
                            "name": section_name,
                            "title": self._section_name_to_title(section_name),
                            "anchor": section_name.replace("_", "-"),
                        }
                    )

        # Add available sections to context for table-of-contents
        context["available_sections"] = available_sections

        # Render ordered sections (supports both .md and .md.j2)
        rendered_content = ""
        for section_name in section_names:
            section_content = self._render_readme_section(section_name, context)
            if section_content:
                rendered_content += f"{section_content}\n\n"

        return [rendered_content]

    def _get_template_context(self) -> dict:
        # Use TOMLDocument from the workdir
        doc = self.workdir.get_project_config()
        project = doc.get("project", {}) if isinstance(doc, dict) else {}

        # Extract information
        description = project.get("description", "")
        python_version = project.get("requires-python", "")
        dependencies = project.get("dependencies", [])
        urls = (
            project.get("urls", {}) if isinstance(project.get("urls", {}), dict) else {}
        )
        # Accept both lowercase and capitalized homepage key variants
        homepage = urls.get("homepage") or urls.get("Homepage") or ""
        license_field = project.get("license", {})
        if isinstance(license_field, dict):
            license_info = license_field.get("text", "") or license_field.get(
                "file", ""
            )
        else:
            license_info = str(license_field) if license_field else ""

        # Format dependencies list
        deps_list = "\n".join([f"- {dep}" for dep in dependencies])

        return {
            "package_name": self.workdir.get_package_name(),
            "version": self.workdir.get_project_version(),
            "description": description,
            "python_version": python_version,
            "dependencies": dependencies,
            "deps_list": deps_list,
            "homepage": homepage,
            "license_info": license_info,
            "workdir": self.workdir,
        }

    def _render_readme_section(self, section_name: str, context: dict) -> str | None:
        """
        Render a README section from .md or .md.j2 file with Jinja2 support.

        Searches in three levels (in order):
        1. Package-level templates
        2. Suite-level templates
        3. Default templates (bundled with the module)

        Tries .md.j2 first, then .md. Both formats support Jinja2 variables.

        Args:
            section_name: Name of the section (without extension)
            context: Jinja2 context variables for rendering

        Returns:
            Rendered content or None if section file not found
        """
        from pathlib import Path

        from jinja2 import Environment, FileSystemLoader, TemplateNotFound
        from wexample_app.const.globals import WORKDIR_SETUP_DIR

        workdir_path = self.workdir.get_path()

        search_paths = [
            workdir_path / WORKDIR_SETUP_DIR / "knowledge" / "readme",  # Package-level
        ]

        # Package may have a suite.
        suite_path = self.workdir.find_suite_workdir_path()
        if suite_path is not None:
            search_paths.append(
                suite_path
                / WORKDIR_SETUP_DIR
                / "knowledge"
                / "package-readme",  # Suite-level
            )

        # Add default templates path (bundled with the module)
        default_templates_path = (
            Path(__file__).parent.parent / "resources" / "readme_templates"
        )
        search_paths.append(default_templates_path)

        # Try .md.j2 first (Jinja2 template)
        for search_path in search_paths:
            if not search_path.exists():
                continue

            env = Environment(loader=FileSystemLoader(str(search_path)))
            try:
                template = env.get_template(f"{section_name}.md.j2")
                return template.render(context)
            except TemplateNotFound:
                pass

        # Try .md (static markdown, still rendered with Jinja2)
        for search_path in search_paths:
            md_path = search_path / f"{section_name}.md"
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                env = Environment(loader=FileSystemLoader(str(search_path)))
                template = env.from_string(content)
                return template.render(context)

        return None

    def _section_exists(self, section_name: str) -> bool:
        """
        Check if a section file exists (.md or .md.j2).

        Searches in three levels:
        1. Package-level templates
        2. Suite-level templates
        3. Default templates (bundled with the module)

        Args:
            section_name: Name of the section (without extension)

        Returns:
            True if section file exists, False otherwise
        """
        from pathlib import Path

        from wexample_app.const.globals import WORKDIR_SETUP_DIR

        workdir_path = self.workdir.get_path()

        search_paths = [
            workdir_path / WORKDIR_SETUP_DIR / "knowledge" / "readme",
        ]

        # Package may have a suite.
        suite_path = self.workdir.find_suite_workdir_path()
        if suite_path is not None:
            search_paths.append(
                suite_path / WORKDIR_SETUP_DIR / "knowledge" / "package-readme",
            )

        # Add default templates path (bundled with the module)
        default_templates_path = (
            Path(__file__).parent.parent / "resources" / "readme_templates"
        )
        search_paths.append(default_templates_path)

        for search_path in search_paths:
            if (search_path / f"{section_name}.md.j2").exists():
                return True
            if (search_path / f"{section_name}.md").exists():
                return True

        return False

    def _section_name_to_title(self, section_name: str) -> str:
        """
        Convert section name to human-readable title.

        Args:
            section_name: Section name (e.g., "basic-usage")

        Returns:
            Human-readable title (e.g., "Basic Usage")
        """
        return section_name.replace("-", " ").replace("_", " ").title()
