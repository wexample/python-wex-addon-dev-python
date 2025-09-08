from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_wex_core.middleware.each_file_middleware import EachFileMiddleware

if TYPE_CHECKING:
    from wexample_wex_core.common.command_request import CommandRequest


class EachPythonFileMiddleware(EachFileMiddleware):
    """
    Middleware for processing Python files only.
    - Filters files by .py extension by default
    - Ignores special directories like __pycache__ during recursion
    """

    # Default list of directories to ignore during recursion
    ignored_directories: set[str] = {
        "__pycache__",
        ".git",
        ".idea",
        ".vscode",
        "venv",
        "env",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
    # Default extension to filter
    python_extension_only: bool = True

    def __init__(self, **kwargs) -> None:
        # Allow overriding the default settings
        if "python_extension_only" in kwargs:
            self.python_extension_only = kwargs.pop("python_extension_only")

        if "ignored_directories" in kwargs:
            self.ignored_directories = set(kwargs.pop("ignored_directories"))

        super().__init__(**kwargs)

    def _should_explore_directory(
        self, request: CommandRequest, directory_name: str
    ) -> bool:
        """
        Skip directories that are in the ignored_directories list.

        Args:
            directory_name: Name of the directory to check

        Returns:
            False if the directory is in the ignored list, True otherwise
        """
        return directory_name not in self.ignored_directories

    def _should_process_item(self, request: CommandRequest, item_path: str) -> bool:
        """
        Only process Python files based on extension.

        Args:
            item_path: Path to the item to check

        Returns:
            True if the item should be processed, False otherwise
        """
        # First check if it's a file (parent class behavior)
        if not os.path.isfile(item_path):
            return False

        # If python_extension_only is enabled, check file extension
        if self.python_extension_only:
            return item_path.endswith(".py")

        # Otherwise, accept all files
        return True
