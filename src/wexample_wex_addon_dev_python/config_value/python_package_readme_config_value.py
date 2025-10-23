from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.config_value.readme_content_config_value import (
    ReadmeContentConfigValue,
)
from wexample_helpers.classes.field import public_field
from wexample_helpers.decorator.base_class import base_class
from wexample_wex_core.const.globals import WORKDIR_SETUP_DIR

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

        # Prepare context for Jinja2 rendering
        context = {
            "package_name": self.workdir.get_package_name(),
            "version": self.workdir.get_project_version(),
            "description": description,
            "python_version": python_version,
            "dependencies": dependencies,
            "deps_list": deps_list,
            "homepage": homepage,
            "license_info": license_info,
        }

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
        
        # Render ordered sections (supports both .md and .md.j2)
        rendered_content = ''
        for section_name in section_names:
            section_content = self._render_readme_section(section_name, context)
            if section_content:
                rendered_content += f"{section_content}\n\n"

        return [rendered_content]

    def _render_readme_section(self, section_name: str, context: dict) -> str | None:
        """
        Render a README section from .md or .md.j2 file with Jinja2 support.
        
        Searches in both package-level and suite-level directories.
        Tries .md.j2 first, then .md. Both formats support Jinja2 variables.
        
        Args:
            section_name: Name of the section (without extension)
            context: Jinja2 context variables for rendering
            
        Returns:
            Rendered content or None if section file not found
        """
        from jinja2 import Environment, FileSystemLoader, TemplateNotFound
        
        workdir_path = self.workdir.get_path()
        suite_path = self.workdir.find_suite_workdir_path()
        
        search_paths = [
            workdir_path / WORKDIR_SETUP_DIR / "knowledge" / "readme",  # Package-level
            suite_path / WORKDIR_SETUP_DIR / "knowledge" / "package-readme",  # Suite-level
        ]
        
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
