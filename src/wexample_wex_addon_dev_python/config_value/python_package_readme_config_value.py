from __future__ import annotations

import os
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
        from jinja2 import Environment, FileSystemLoader

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

        workdir_path = self.workdir.get_path()
        env = Environment(loader=FileSystemLoader(workdir_path / WORKDIR_SETUP_DIR / "doc" / "readme"))
        template = env.get_template("introduction.md.j2")
        context = {}

        package_name = self.workdir.get_package_name()
        return [
            f"# {package_name}\n\n"
            f"{description}\n\n"
            f"Version: {self.workdir.get_project_version()}\n\n"
            f'{self._add_section_if_exists("features")}'
            "## Introduction\n"
            f"{template.render(context)}\n\n"
            "## Requirements\n\n"
            f"- Python {python_version}\n\n"
            "## Dependencies\n\n"
            f"{deps_list}\n\n"
            "## Installation\n\n"
            "```bash\n"
            f"pip install {package_name}\n"
            "```\n\n"
            f'{self._add_section_if_exists("usage")}'
            "## Links\n\n"
            f"- Homepage: {homepage}\n\n"
            "## License\n\n"
            f"{license_info}\n"
        ]

    def _add_section_if_exists(self, section: str) -> str:
        """
        Returns section content if the documentation file exists
        """
        doc_path = self._get_doc_path(section)

        if os.path.exists(doc_path):
            with open(doc_path, encoding="utf-8") as file:
                content = file.read()
                return f"## {section.title()}\n\n{content}\n\n"

        return ""

    def _get_doc_path(self, section: str) -> str:
        """
        Returns the path to a documentation section file
        """
        return os.path.join(
            self.workdir.get_path(), ".wex", "doc", "readme", f"{section}.md"
        )
