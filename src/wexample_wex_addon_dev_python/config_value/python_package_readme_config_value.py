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

    def _get_readme_search_paths(self):
        from pathlib import Path
        from wexample_app.const.globals import WORKDIR_SETUP_DIR

        workdir_path = self.workdir.get_path()

        search_paths = [
            workdir_path / WORKDIR_SETUP_DIR / "knowledge" / "readme",
            ]

        # Suite-level templates
        suite_path = self.workdir.find_suite_workdir_path()
        if suite_path is not None:
            search_paths.append(
                suite_path / WORKDIR_SETUP_DIR / "knowledge" / "package-readme"
            )

        # Default templates (bundled)
        default_templates_path = (
                Path(__file__).parent.parent / "resources" / "readme_templates"
        )
        search_paths.append(default_templates_path)

        return search_paths

    def get_templates(self) -> list[str] | None:
        context = self._get_template_context()

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

        # Collect available sections
        available_sections = []
        for section_name in section_names:
            if section_name not in ["title", "table-of-contents"]:
                if self._section_exists(section_name):
                    available_sections.append(
                        {
                            "name": section_name,
                            "title": self._section_name_to_title(section_name),
                            "anchor": section_name.replace("_", "-"),
                        }
                    )

        context["available_sections"] = available_sections

        # Render in order
        rendered_content = ""
        for section_name in section_names:
            section_content = self._render_readme_section(section_name, context)
            if section_content:
                rendered_content += f"{section_content}\n\n"

        return [rendered_content]

    def _get_template_context(self) -> dict:
        doc = self.workdir.get_project_config()
        project = doc.get("project", {}) if isinstance(doc, dict) else {}

        description = project.get("description", "")
        python_version = project.get("requires-python", "")
        dependencies = project.get("dependencies", [])
        urls = project.get("urls", {}) if isinstance(project.get("urls", {}), dict) else {}

        homepage = urls.get("homepage") or urls.get("Homepage") or ""

        license_field = project.get("license", {})
        if isinstance(license_field, dict):
            license_info = license_field.get("text", "") or license_field.get("file", "")
        else:
            license_info = str(license_field) if license_field else ""

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
        from jinja2 import Environment, FileSystemLoader, TemplateNotFound

        search_paths = self._get_readme_search_paths()

        # Try .md.j2 first
        for search_path in search_paths:
            if not search_path.exists():
                continue

            env = Environment(loader=FileSystemLoader(str(search_path)))
            try:
                template = env.get_template(f"{section_name}.md.j2")
                return template.render(context)
            except TemplateNotFound:
                pass

        # Then try .md
        for search_path in search_paths:
            md_path = search_path / f"{section_name}.md"
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                env = Environment(loader=FileSystemLoader(str(search_path)))
                template = env.from_string(content)
                return template.render(context)

        return None

    def _section_exists(self, section_name: str) -> bool:
        for search_path in self._get_readme_search_paths():
            if (search_path / f"{section_name}.md.j2").exists():
                return True
            if (search_path / f"{section_name}.md").exists():
                return True
        return False

    def _section_name_to_title(self, section_name: str) -> str:
        return section_name.replace("-", " ").replace("_", " ").title()
