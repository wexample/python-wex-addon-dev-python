from __future__ import annotations

# Names of dev/build tools to remove from runtime [project.dependencies]
# Keep this list in sync with tooling expectations.
REMOVE_NAMES: set[str] = {
    "pytest",
    "pip-tools",
    "black",
    "ruff",
    "flake8",
    "mypy",
    "isort",
    "coverage",
    "build",
    "twine",
    "pip",
    "setuptools",
    "wheel",
    "typing-extensions",
}

