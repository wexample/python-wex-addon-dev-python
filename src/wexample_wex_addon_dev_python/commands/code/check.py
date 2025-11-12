from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_wex_core.const.middleware import (
    MIDDLEWARE_OPTION_VALUE_ALLWAYS,
    MIDDLEWARE_OPTION_VALUE_OPTIONAL,
)
from wexample_wex_core.decorator.command import command
from wexample_wex_core.decorator.middleware import middleware
from wexample_wex_core.decorator.option import option
from wexample_wex_core.decorator.option_stop_on_failure import option_stop_on_failure

if TYPE_CHECKING:
    from wexample_wex_core.context.execution_context import ExecutionContext


@option(
    name="tool",
    type=str,
    required=False,
    description="Specific tool to run (mypy, pylint, pyright). If not specified, all tools will be run.",
)
@option_stop_on_failure()
@middleware(
    name="each_python_file",
    should_exist=True,
    expand_glob=True,
    stop_on_failure=MIDDLEWARE_OPTION_VALUE_OPTIONAL,
    recursive=True,
    parallel=MIDDLEWARE_OPTION_VALUE_OPTIONAL,
    show_progress=MIDDLEWARE_OPTION_VALUE_ALLWAYS,
)
@command(
    description="Check python code on every file: "
    "bash cli/wex python::code/check --file ../../pip/wex-core/wexample_wex_core/ -sof"
)
def python__code__check(
    context: ExecutionContext,
    file: str,
    tool: str | None = None,
    stop_on_failure: bool = True,
    parallel: bool = True,
) -> bool:
    """Check a Python file using various code quality tools."""
    from wexample_app.response.failure_response import FailureResponse

    from wexample_wex_addon_dev_python.commands.code.check.mypy import _code_check_mypy
    from wexample_wex_addon_dev_python.commands.code.check.pylint import (
        _code_check_pylint,
    )
    from wexample_wex_addon_dev_python.commands.code.check.pyright import (
        _code_check_pyright,
    )

    # Map tool names to their check functions
    tool_map = {
        "mypy": _code_check_mypy,
        "pylint": _code_check_pylint,
        "pyright": _code_check_pyright,
    }

    # Determine which tools to run
    if tool and tool.lower() in tool_map:
        # Run only the specified tool
        check_functions = [tool_map[tool.lower()]]
    else:
        # Run all tools if no specific tool is specified or if the specified tool is invalid
        check_functions = [
            _code_check_mypy,
            _code_check_pylint,
            _code_check_pyright,
        ]

    # Track overall success
    all_checks_passed = True

    # Run each check function
    for check_function in check_functions:
        context.io.title(check_function.__name__)
        context.io.log_indent_up()

        context.io.log(
            f"🐍 Python: {context.kernel.host_workdir.render_display_path(file)}"
        )

        check_result = check_function(context, file)

        if check_result:
            context.io.success(f"No critical issue found for {check_function.__name__}")

        # Update overall success status
        all_checks_passed = all_checks_passed and check_result

        # Stop if a check fails and stop_on_failure is True
        if not check_result and stop_on_failure:
            context.io.error("One check failed")

            context.io.log_indent_down()

            return FailureResponse(message="One check failed", kernel=context.kernel)

        context.io.log_indent_down()
    return all_checks_passed
