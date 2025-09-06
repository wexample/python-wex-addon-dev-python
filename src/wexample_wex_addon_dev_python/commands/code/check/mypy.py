from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wexample_wex_core.common.kernel import Kernel


def _code_check_mypy(kernel: Kernel, file_path: str) -> bool:
    """Check a Python file using mypy for static type checking.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to check

    Returns:
        bool: True if check passes, False otherwise
    """
    import sys

    from mypy import build
    from mypy.modulefinder import BuildSource
    from mypy.options import Options

    # Configure mypy options
    options = Options()
    options.python_version = sys.version_info[:2]
    options.show_traceback = True
    options.disallow_untyped_defs = True
    options.disallow_incomplete_defs = True

    # Ignore import as file might be placed anywhere, we have no more context.
    options.ignore_missing_imports = True

    # Build and check the file
    source = BuildSource(path=file_path, module=None, text=None)
    result = build.build(sources=[source], options=options, alt_lib_path=None)
    if result.errors:
        kernel.io.log_indent_up()
        kernel.io.error(f"Mypy errors:")
        kernel.io.log_indent_up()

        for error in result.errors:
            kernel.io.error(message=error, symbol=False)

        kernel.io.log_indent_down(number=2)
        return False
    return True
