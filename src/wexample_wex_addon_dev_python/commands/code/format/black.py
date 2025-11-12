from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wexample_wex_core.common.kernel import Kernel


def _code_format_black(kernel: Kernel, file_path: str) -> bool:
    """Format a Python file using Black.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to format

    Returns:
        bool: True if formatting succeeds, False otherwise
    """
    import subprocess
    import sys

    # Use subprocess to run black
    cmd = [sys.executable, "-m", "black", file_path]
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Check if the command was successful
    if process.returncode == 0:
        if "reformatted" in process.stderr or "reformatted" in process.stdout:
            kernel.io.success(f"Black successfully reformatted {file_path}")
        else:
            kernel.io.success(f"Black: {file_path} already well formatted")
        return True
    else:
        kernel.io.error(f"Black failed to format {file_path}")
        kernel.io.log_indent_up()

        if process.stderr:
            kernel.io.error(f"Error: {process.stderr}", symbol=False)
        if process.stdout:
            kernel.io.error(f"Output: {process.stdout}", symbol=False)

        # Add detailed error properties
        kernel.io.properties({"returncode": process.returncode, "command": cmd})

        kernel.io.log_indent_down()
        return False
