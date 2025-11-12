from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wexample_wex_core.context.execution_context import ExecutionContext


def _code_check_pylint(context: ExecutionContext, file_path: str) -> bool:
    """Check a Python file using pylint for code quality.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to check

    Returns:
        bool: True if check passes, False otherwise
    """
    import json
    import subprocess
    import sys

    # Use subprocess to capture pylint output
    # This avoids issues with pylint's direct printing to stdout
    # List of warnings to disable
    disabled_warnings = [
        "missing-module-docstring",
        "import-outside-toplevel",
        "no-name-in-module",
        "broad-exception-caught",
        "c-extension-no-member",
        "line-too-long",
    ]

    cmd = [
        sys.executable,
        "-m",
        "pylint",
        file_path,
        "--output-format=json",
        f"--disable={','.join(disabled_warnings)}",
    ]
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Get the output from stdout
    json_output = process.stdout.strip()

    # If no output or invalid JSON, return empty list
    if not json_output:
        context.io.success(f"No pylint issues found in {file_path}")
        return True

    # Parse the JSON output
    results = json.loads(json_output)

    # Filter messages by type
    errors = [msg for msg in results if msg.get("type") in ("error", "fatal")]
    warnings = [msg for msg in results if msg.get("type") == "warning"]
    conventions = [
        msg for msg in results if msg.get("type") in ("convention", "refactor", "info")
    ]

    # Display results if any issues found
    if errors or warnings or conventions:
        # Display errors
        if errors:
            context.io.log_indent_up()
            context.io.error(f"Pylint errors:")
            context.io.log_indent_up()

            for error in errors:
                context.io.error(
                    message=f"Line {error.get('line')}: "
                    f"{error.get('message')} ({error.get('symbol')})",
                    symbol=False,
                )

            context.io.log_indent_down(number=2)

        # Display warnings with detailed logging
        if warnings:
            context.io.log_indent_up()
            context.io.warning(f"Pylint warnings:")
            context.io.log_indent_up()

            for warning in warnings:
                context.io.warning(
                    f"Line {warning.get('line')}: "
                    f"{warning.get('message')} ({warning.get('symbol')})",
                    symbol=False,
                )
                context.io.properties(warning)

            context.io.log_indent_down(number=2)
        # Display conventions
        if conventions:
            context.io.info("Conventions:")
            for convention in conventions:
                context.io.base(
                    message=f"  Line {convention.get('line')}: "
                    f"{convention.get('message')} ({convention.get('symbol')})"
                )

        # Only consider errors as failures
        if errors:
            return False
        return True
    return True
