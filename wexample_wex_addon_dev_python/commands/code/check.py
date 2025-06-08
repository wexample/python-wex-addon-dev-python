import os
from typing import List, Callable

from wexample_wex_core.common.kernel import Kernel
from wexample_wex_core.decorator.command import command
from wexample_wex_core.decorator.option import option


@option(name="file_path", type=str, required=True)
@command()
def python__code__check(
        kernel: "Kernel",
        file_path: str
) -> bool:
    from wexample_wex_addon_dev_python.commands.code.check.mypy import _code_check_mypy
    from wexample_wex_addon_dev_python.commands.code.check.pylint import _code_check_pylint
    from wexample_wex_addon_dev_python.commands.code.check.pyright import _code_check_pyright

    """Check a Python file using various code quality tools.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to check

    Returns:
        bool: True if all checks pass, False otherwise
    """
    if not os.path.exists(file_path):
        kernel.io.error(f"Error: File {file_path} does not exist")
        return False

    CODE_CHECKS: List[Callable[["Kernel", str], bool]] = [
        _code_check_mypy,
        _code_check_pylint,
        _code_check_pyright,
    ]

    for check_function in CODE_CHECKS:
        kernel.io.title(check_function.__name__)
        if not check_function(kernel, file_path):
            return False

    return True
