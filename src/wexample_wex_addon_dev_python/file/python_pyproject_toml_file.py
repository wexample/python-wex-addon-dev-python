from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_filestate.item.file.toml_file import TomlFile
from wexample_helpers.decorator.base_class import base_class
from wexample_wex_addon_app.const.path import APP_PATH_README

if TYPE_CHECKING:
    from tomlkit import TOMLDocument


@base_class
class PythonPyprojectTomlFile(TomlFile):
    def add_dependency(
        self,
        package_name: str,
        version: str,
        operator: str = "==",
        optional: bool = False,
        group: None | str = None,
    ) -> bool:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
        from wexample_filestate_python.helpers.toml import toml_sort_string_array

        spec = f"{package_name}{operator}{version}"
        new_req = Requirement(spec)
        new_name = canonicalize_name(new_req.name)

        deps = self._get_deps_array(optional=optional, group=group)

        # Look for existing dependency
        old_spec = next(
            (d for d in deps if canonicalize_name(Requirement(d).name) == new_name),
            None,
        )

        # Remove old dep if exists
        if old_spec:
            deps.remove(old_spec)

        # Add new version
        deps.append(spec)

        # Sort array
        toml_sort_string_array(deps)

        # Save file
        self.write_parsed()

        return old_spec != spec

    def dumps(self, content: TOMLDocument | dict | None = None) -> str:
        """Serialize a TOMLDocument (preferred) or a plain dict to TOML.
        Using tomlkit.dumps preserves comments/formatting when content is a TOMLDocument.
        """
        from tomlkit import dumps

        content = content or self.read_parsed()

        workdir = self.get_parent_item()
        import_name = workdir.get_package_import_name()
        project_name = workdir.get_package_name()
        project_version = workdir.get_project_version()

        self._enforce_build_system(content)
        self._enforce_pdm_build(content, import_name)
        self._enforce_project_metadata(content, project_name, project_version)
        self._normalize_dependencies(content)
        self._ensure_dev_dependencies(content)
        self._enforce_pytest_coverage_config(content, import_name)
        self._reorder_toml_sections(content)

        result = dumps(content)
        result = self._normalize_toml_formatting(result)

        return result

    def get_dependencies_versions(
        self, optional: bool = False, group: str = "dev"
    ) -> dict[str, str]:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        deps = self._get_deps_array(optional=optional, group=group)

        map = {}
        for spec in list(deps):
            req = Requirement(spec)
            # name: version
            map[canonicalize_name(req.name)] = str(req.specifier)

        return map

    def optional_group_array(self, group: str):
        """Ensure and return project.optional-dependencies[group] as multi-line array."""
        from wexample_filestate_python.helpers.toml import (
            toml_ensure_array,
            toml_ensure_table,
        )

        project = self._project_table()
        opt, _ = toml_ensure_table(project, ["optional-dependencies"])
        arr, _ = toml_ensure_array(opt, group)
        arr.multiline(True)
        return arr

    def remove_dependency_by_name(
        self, package_name: str, optional: bool = False, group: str = "dev"
    ) -> bool:
        """Remove all dependency entries that match the given package name.

        The provided package_name can be raw; it will be canonicalized to ensure
        consistent matching against entries parsed from list_dependencies().
        """
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        deps = self._get_deps_array(optional=optional, group=group)

        target = canonicalize_name(package_name)
        filtered: list[str] = []
        for existing in list(deps):
            try:
                existing_name = canonicalize_name(Requirement(str(existing)).name)
            except Exception:
                # Keep unparsable entries untouched
                filtered.append(existing)
                continue
            if existing_name != target:
                filtered.append(existing)

        if len(filtered) != len(deps):
            deps.clear()
            deps.extend(filtered)
            return True
        return False

    def _dependencies_array(self):
        """Ensure and return project.dependencies as a multi-line TOML array."""
        from wexample_filestate_python.helpers.toml import toml_ensure_array

        project = self._project_table()
        deps, _ = toml_ensure_array(project, "dependencies")
        deps.multiline(True)
        return deps

    def _enforce_build_system(self, content: dict) -> None:
        from tomlkit import table

        build_tbl = content.get("build-system")
        if not isinstance(build_tbl, dict):
            build_tbl = table()
            content["build-system"] = build_tbl
        build_tbl["requires"] = ["pdm-backend"]
        build_tbl["build-backend"] = "pdm.backend"

    def _enforce_pdm_build(self, content: dict, import_name: str | None) -> None:
        from wexample_filestate_python.helpers.toml import toml_ensure_table

        tool_tbl, _ = toml_ensure_table(content, ["tool"])
        pdm_tbl, _ = toml_ensure_table(tool_tbl, ["pdm"])
        build_pdm_tbl, _ = toml_ensure_table(pdm_tbl, ["build"])

        pdm_tbl["distribution"] = True
        build_pdm_tbl["package-dir"] = "src"
        if import_name:
            build_pdm_tbl["packages"] = [{"include": import_name, "from": "src"}]
            build_pdm_tbl.pop("includes", None)

        # Add setuptools exclusion of testing package
        setuptools_tbl, _ = toml_ensure_table(tool_tbl, ["setuptools"])
        find_tbl, _ = toml_ensure_table(setuptools_tbl, ["packages", "find"])
        find_tbl["include"] = ["*"]
        find_tbl["exclude"] = [f"{import_name}.testing*"]

    def _enforce_project_metadata(
        self, content: dict, project_name: str | None, project_version: str | None
    ) -> None:
        from wexample_filestate_python.helpers.toml import toml_ensure_table

        project_tbl, _ = toml_ensure_table(content, ["project"])
        if project_name:
            project_tbl["name"] = project_name
        if project_version:
            project_tbl["version"] = project_version
        # Only set requires-python if not already defined
        if "requires-python" not in project_tbl:
            project_tbl["requires-python"] = ">=3.10"

        # Add description if available
        workdir = self.get_parent_item()
        description = workdir.get_config().search("global.description")
        if not description.is_none():
            project_tbl["description"] = description.get_str()

        # Add authors if available
        from tomlkit import array, inline_table

        author_name = workdir.search_in_package_or_suite_config("global.authors.name")
        author_email = workdir.search_in_package_or_suite_config("global.authors.email")

        if not author_name.is_none() or not author_email.is_none():
            authors_arr = array()
            author_tbl = inline_table()

            if not author_name.is_none():
                author_tbl["name"] = author_name.get_str()
            if not author_email.is_none():
                author_tbl["email"] = author_email.get_str()

            authors_arr.append(author_tbl)
            project_tbl["authors"] = authors_arr

        # Add classifiers (standard Python package metadata)
        project_tbl["classifiers"] = [
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ]

        # Add README if it exists
        readme_file = workdir.find_by_name(APP_PATH_README)
        if readme_file:
            readme_tbl, _ = toml_ensure_table(project_tbl, ["readme"])
            readme_tbl["file"] = str(APP_PATH_README)
            readme_tbl["content-type"] = "text/markdown"

        # Add MIT license
        license_tbl, _ = toml_ensure_table(project_tbl, ["license"])
        license_tbl["text"] = "MIT"

    def _enforce_pytest_coverage_config(
        self, content: dict, import_name: str | None
    ) -> None:
        """Add pytest and coverage configuration to limit coverage to the package only."""
        if not import_name:
            return

        from wexample_filestate_python.helpers.toml import toml_ensure_table

        tool_tbl, _ = toml_ensure_table(content, ["tool"])

        # Add pytest configuration
        pytest_tbl, _ = toml_ensure_table(tool_tbl, ["pytest", "ini_options"])
        pytest_tbl["testpaths"] = ["tests"]
        pytest_tbl["pythonpath"] = ["src"]

        # Add coverage.run configuration to limit source to the package
        coverage_run_tbl, _ = toml_ensure_table(tool_tbl, ["coverage", "run"])
        coverage_run_tbl["source"] = [import_name]
        coverage_run_tbl["omit"] = [
            "*/tests/*",
            "*/.venv/*",
            "*/venv/*",
        ]

        # Add coverage.report configuration
        coverage_report_tbl, _ = toml_ensure_table(tool_tbl, ["coverage", "report"])
        coverage_report_tbl["exclude_lines"] = [
            "pragma: no cover",
            "def __repr__",
            "raise AssertionError",
            "raise NotImplementedError",
            "if __name__ == .__main__.:",
            "if TYPE_CHECKING:",
            "@abstractmethod",
        ]

    def _ensure_dev_dependencies(self, content: dict) -> None:
        from wexample_filestate_python.helpers.package import package_normalize_name
        from wexample_filestate_python.helpers.toml import (
            toml_get_string_value,
            toml_sort_string_array,
        )

        dev_arr = self.optional_group_array("dev")
        deps_arr = self._dependencies_array()

        runtime_pkgs = {
            package_normalize_name(toml_get_string_value(it)) for it in list(deps_arr)
        }
        dev_values = [toml_get_string_value(it).strip() for it in list(dev_arr)]

        for pkg in ["pytest", "pytest-cov"]:
            if pkg not in runtime_pkgs and pkg not in dev_values:
                dev_arr.append(pkg)

        toml_sort_string_array(dev_arr)

    def _get_deps_array(self, optional: bool = False, group: str = "dev"):
        """Return TOML array for runtime deps or optional group (multiline)."""
        return (
            self.optional_group_array(group) if optional else self._dependencies_array()
        )

    def _normalize_dependencies(self, content: dict) -> None:
        from wexample_filestate_python.helpers.package import package_normalize_name
        from wexample_filestate_python.helpers.toml import (
            toml_get_string_value,
            toml_sort_string_array,
        )

        from wexample_wex_addon_dev_python.const.package import (
            RUNTIME_DEPENDENCY_REMOVE_NAMES,
        )

        deps_arr = self._dependencies_array()
        toml_sort_string_array(deps_arr)

        # Read the keep list from [tool.filestate].keep
        keep_packages: set[str] = set()
        if "tool" in content and isinstance(content["tool"], dict):
            tool_tbl = content["tool"]
            if "filestate" in tool_tbl and isinstance(tool_tbl["filestate"], dict):
                filestate_tbl = tool_tbl["filestate"]
                if "keep" in filestate_tbl and isinstance(filestate_tbl["keep"], list):
                    keep_packages = {
                        package_normalize_name(str(pkg))
                        for pkg in filestate_tbl["keep"]
                    }

        # filter unwanted deps
        def _should_remove(item: object) -> bool:
            name = package_normalize_name(toml_get_string_value(item))
            # Don't remove if in keep list
            if name in keep_packages:
                return False
            return name in RUNTIME_DEPENDENCY_REMOVE_NAMES or (
                name == "typing-extensions"
            )

        filtered = [it for it in deps_arr if not _should_remove(it)]
        deps_arr.clear()
        deps_arr.extend(filtered)
        toml_sort_string_array(deps_arr)

    def _normalize_toml_formatting(self, content: str) -> str:
        """Normalize TOML formatting:
        - No empty lines at the beginning
        - Single newline at the end
        - No double newlines between sections
        """
        import re

        # Remove leading empty lines
        content = content.lstrip("\n")

        # Replace multiple consecutive newlines with single newline
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Ensure exactly one newline at the end
        content = content.rstrip("\n") + "\n"

        return content

    def _project_table(self):
        """Ensure and return the [project] table."""
        from wexample_filestate_python.helpers.toml import toml_ensure_table

        doc = self.read_parsed()
        project, _ = toml_ensure_table(doc, ["project"])
        return project

    def _reorder_dict_keys(self, d: dict, key_order: list[str]) -> None:
        """Reorder dictionary keys according to the specified order.
        Keys not in key_order will appear after ordered keys in their original order.
        """
        # Get all existing keys
        existing_keys = list(d.keys())

        # Build the new order: ordered keys first, then remaining keys
        ordered_keys = [k for k in key_order if k in existing_keys]
        remaining_keys = [k for k in existing_keys if k not in key_order]
        new_order = ordered_keys + remaining_keys

        # Reorder by removing and re-adding in the desired order
        for key in new_order:
            value = d.pop(key)
            d[key] = value

    def _reorder_toml_sections(self, content: dict) -> None:
        """Reorder TOML sections and keys for consistent output."""
        # Define the desired order for top-level sections
        section_order = [
            "build-system",
            "project",
            "tool",
        ]

        # Define the desired order for keys within [project]
        project_key_order = [
            "name",
            "version",
            "description",
            "authors",
            "requires-python",
            "classifiers",
            "dependencies",
            "readme",
            "license",
            "urls",
            "optional-dependencies",
        ]

        # Define the desired order for keys within [tool]
        tool_key_order = [
            "setuptools",
            "pdm",
            "pytest",
            "coverage",
        ]

        # Reorder top-level sections
        self._reorder_dict_keys(content, section_order)

        # Reorder keys within [project] if it exists
        if "project" in content:
            self._reorder_dict_keys(content["project"], project_key_order)

        # Reorder keys within [tool] if it exists
        if "tool" in content:
            self._reorder_dict_keys(content["tool"], tool_key_order)
