import os
import sys

from wexample_wex_core.common.kernel import Kernel
from wexample_wex_core.decorator.command import command
from wexample_wex_core.decorator.option import option


@option(name="file_path", type=str, required=True)
@command()
def python__code__check(
        kernel: "Kernel",
        file_path: str
) -> bool:
    """Check a Python file using mypy for static type checking.
    
    Args:
        kernel: The application kernel
        file_path: Path to the Python file to check
    """
    if not os.path.exists(file_path):
        kernel.io.error(f"Error: File {file_path} does not exist")
        return False

    try:
        # Import mypy modules
        from mypy import build
        from mypy.options import Options
        from mypy.errors import CompileError

        # Configure mypy options
        options = Options()
        options.python_version = sys.version_info[:2]
        options.show_traceback = True
        options.disallow_untyped_defs = True
        options.disallow_incomplete_defs = True

        # Build and check the file
        try:
            result = build.build(sources=[file_path], options=options, alt_lib_path=None)
            if result.errors:
                kernel.io.error(f"Type checking failed for {file_path}:")
                for error in result.errors:
                    kernel.io.error(f"  {error}")
            else:
                kernel.io.success(f"Type checking passed for {file_path}")
                return True
        except CompileError as e:
            kernel.io.error(f"Error during type checking: {e}")
    except Exception as e:
        kernel.io.error(exception=e)

    return False
