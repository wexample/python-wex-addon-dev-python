from __future__ import annotations

# Names of dev/build tools to remove from runtime [project.dependencies]
# Keep this list in sync with tooling expectations.
RUNTIME_DEPENDENCY_REMOVE_NAMES: set[str] = {
    # filestate: python-iterable-sort
    "black",
    "build",
    "coverage",
    "flake8",
    "isort",
    "mypy",
    "pip",
    "pip-tools",
    "pytest",
    "ruff",
    "setuptools",
    "twine",
    "typing-extensions",
    "wheel",
}
