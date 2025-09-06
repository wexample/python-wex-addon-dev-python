from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_wex_core.decorator.command import command
from wexample_wex_core.decorator.middleware import middleware
from wexample_wex_core.decorator.option import option

if TYPE_CHECKING:
    from wexample_wex_core.common.kernel import Kernel


@option(
    name="tool",
    type=str,
    required=False,
    description="Specific tool to run (black, isort). If not specified, all tools will be run.",
)
@option(
    name="stop_on_failure",
    type=bool,
    required=False,
    default=True,
    description="Stop execution when a tool reports a failure",
)
@middleware(
    name="each_python_file", should_exist=True, expand_glob=True, recursive=True
)
@command()
def python__code__format(
    kernel: Kernel,
    file: str,
    tool: str | None = None,
    stop_on_failure: bool = True,
) -> bool:
    """Format a Python file using various code formatting tools."""
    from wexample_wex_addon_dev_python.commands.code.format.black import (
        _code_format_black,
    )
    from wexample_wex_addon_dev_python.commands.code.format.isort import (
        _code_format_isort,
    )

    # Map tool names to their format functions
    tool_map = {
        "black": _code_format_black,
        "isort": _code_format_isort,
    }

    # Determine which tools to run
    if tool and tool.lower() in tool_map:
        # Run only the specified tool
        format_functions = [tool_map[tool.lower()]]
    else:
        # Run all tools if no specific tool is specified or if the specified tool is invalid
        if tool and tool.lower() not in tool_map:
            kernel.io.warning(f"Unknown tool '{tool}', running all available tools")

        # Run isort first, then black (recommended order)
        format_functions = [
            _code_format_isort,
            _code_format_black,
        ]

    # Track overall success
    all_formats_passed = True

    # Run each format function
    for format_function in format_functions:
        kernel.io.title(format_function.__name__)
        format_result = format_function(kernel, file)

        # Update overall success status
        all_formats_passed = all_formats_passed and format_result

        # Stop if a format fails and stop_on_failure is True
        if not format_result and stop_on_failure:
            kernel.io.warning("One formatting failed")
            return False

    return all_formats_passed
