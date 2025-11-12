from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wexample_wex_core.common.kernel import Kernel


def _code_check_pyright(kernel: Kernel, file_path: str) -> bool:
    """Check a Python file using pyright for static type checking.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to check

    Returns:
        bool: True if check passes, False otherwise
    """
    import json
    import subprocess
    import sys

    # Use subprocess to run pyright
    cmd = [sys.executable, "-m", "pyright", file_path, "--outputjson"]
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Get the output from stdout
    json_output = process.stdout.strip()

    # If command failed or no output, handle the error
    if process.returncode != 0 and not json_output:
        kernel.io.error(f"Pyright failed to run on {file_path}")
        if process.stderr:
            kernel.io.error(f"Error: {process.stderr}")
        return False

    # If no output, assume success
    if not json_output:
        kernel.io.success(f"No pyright issues found in {file_path}")
        return True

    # Parse the JSON output
    results = json.loads(json_output)

    # Extract diagnostics
    diagnostics = results.get("diagnostics", [])

    # Filter by severity
    errors = [diag for diag in diagnostics if diag.get("severity") == "error"]
    warnings = [diag for diag in diagnostics if diag.get("severity") == "warning"]
    info = [diag for diag in diagnostics if diag.get("severity") == "information"]

    # Display results if any issues found
    if errors or warnings or info:
        # Display errors
        if errors:
            kernel.io.log_indent_up()
            kernel.io.error(f"Pyright errors:")

            for error in errors:
                line = error.get("range", {}).get("start", {}).get("line", 0) + 1
                message = error.get("message", "Unknown error")
                rule = error.get("rule", "")
                rule_text = f" ({rule})" if rule else ""
                kernel.io.error(f"Line {line}: {message}{rule_text}", symbol=False)
                kernel.io.properties(error)

            kernel.io.log_indent_down(number=2)

        # Display warnings
        if warnings:
            kernel.io.log_indent_up()
            kernel.io.warning(f"Pyright warnings:")

            for warning in warnings:
                line = warning.get("range", {}).get("start", {}).get("line", 0) + 1
                message = warning.get("message", "Unknown warning")
                rule = warning.get("rule", "")
                rule_text = f" ({rule})" if rule else ""
                kernel.io.warning(f"Line {line}: {message}{rule_text}", symbol=False)
                kernel.io.properties(warning)

            kernel.io.log_indent_down(number=2)

        # Display information
        if info:
            kernel.io.log_indent_up()
            kernel.io.info(f"Pyright information:")
            kernel.io.log_indent_up()

            for item in info:
                line = item.get("range", {}).get("start", {}).get("line", 0) + 1
                message = item.get("message", "Unknown info")
                rule = item.get("rule", "")
                rule_text = f" ({rule})" if rule else ""
                kernel.io.info(f"Line {line}: {message}{rule_text}", symbol=False)
                kernel.io.properties(item)

            kernel.io.log_indent_down(number=2)

        # Only consider errors as failures
        if errors:
            return False
    return True
