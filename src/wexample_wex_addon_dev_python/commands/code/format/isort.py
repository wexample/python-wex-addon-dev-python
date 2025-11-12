from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wexample_wex_core.common.kernel import Kernel


def _code_format_isort(kernel: Kernel, file_path: str) -> bool:
    """Format imports in a Python file using isort.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to format

    Returns:
        bool: True if formatting succeeds, False otherwise
    """
    import subprocess
    import sys

    # Use subprocess to run isort
    # --profile=black ensures compatibility with Black formatter
    cmd = [sys.executable, "-m", "isort", "--profile=black", file_path]
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Check if the command was successful
    if process.returncode == 0:
        if "Skipped" in process.stdout:
            kernel.io.success(f"isort: {file_path} already well formatted")
        else:
            kernel.io.success(f"isort successfully reformatted imports in {file_path}")
        return True
    else:
        kernel.io.error(f"isort failed to format imports in {file_path}")
        kernel.io.log_indent_up()

        if process.stderr:
            kernel.io.error(f"Error: {process.stderr}", symbol=False)
        if process.stdout:
            kernel.io.error(f"Output: {process.stdout}", symbol=False)

        # Add detailed error properties
        kernel.io.properties({"returncode": process.returncode, "command": cmd})

        kernel.io.log_indent_down()
        return False
