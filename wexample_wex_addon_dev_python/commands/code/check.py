import os
import sys
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
    ]

    for check_function in CODE_CHECKS:
        kernel.io.title(check_function.__name__)
        if not check_function(kernel, file_path):
            return False

    return True


def _code_check_mypy(kernel: "Kernel", file_path: str) -> bool:
    """Check a Python file using mypy for static type checking.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to check

    Returns:
        bool: True if check passes, False otherwise
    """
    try:
        # Import mypy modules
        from mypy import build
        from mypy.options import Options
        from mypy.errors import CompileError
        from mypy.modulefinder import BuildSource

        # Configure mypy options
        options = Options()
        options.python_version = sys.version_info[:2]
        options.show_traceback = True
        options.disallow_untyped_defs = True
        options.disallow_incomplete_defs = True

        # Ignore import as file might be placed anywhere, we have no more context.
        options.ignore_missing_imports = True

        # Build and check the file
        try:
            source = BuildSource(path=file_path, module=None, text=None)
            result = build.build(sources=[source], options=options, alt_lib_path=None)
            if result.errors:
                kernel.io.error(f"Type checking failed for {file_path}:")
                for error in result.errors:
                    kernel.io.base(message=f"  {error}")
                return False
            else:
                kernel.io.success(f"Type checking passed for {file_path}")
                return True
        except CompileError as e:
            kernel.io.error(f"Error during type checking: {e}")
        except Exception as e:
            kernel.io.error(f"Unexpected error during type checking: {e}")
            import traceback
            traceback.print_exc()
    except ImportError:
        kernel.io.error("mypy is not installed. Please install it with 'pip install mypy'")
    except Exception as e:
        kernel.io.error(exception=e)

    return False


def _code_check_pylint(kernel: "Kernel", file_path: str) -> bool:
    """Check a Python file using pylint for code quality.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to check

    Returns:
        bool: True if check passes, False otherwise
    """
    # Import pylint modules
    from pylint.lint import Run
    from pylint.reporters.json_reporter import JSONReporter
    import io
    import json

    # Préparer le reporter pour capturer la sortie
    output = io.StringIO()
    reporter = JSONReporter(output)

    # Options de pylint
    options = [
        file_path,
        "--output-format=json",
    ]

        try:
            Run(options, reporter=reporter, exit=False)
    Run(options, reporter=reporter, exit=False)

            results = json.loads(output.getvalue())

            errors = [msg for msg in results if msg.get('type') in ('error', 'fatal')]
            warnings = [msg for msg in results if msg.get('type') == 'warning']
            conventions = [msg for msg in results if msg.get('type') in ('convention', 'refactor', 'info')]

    results = json.loads(output.getvalue())
    errors = [msg for msg in results if msg.get('type') in ('error', 'fatal')]
    warnings = [msg for msg in results if msg.get('type') == 'warning']
    conventions = [msg for msg in results if msg.get('type') in ('convention', 'refactor', 'info')]

    if errors or warnings or conventions:
        if errors:
            kernel.io.error(f"Pylint found errors in {file_path}:")
            kernel.io.error("Errors:")
            for error in errors:
                kernel.io.base(
                    message=f"  Line {error.get('line')}: {error.get('message')} ({error.get('symbol')})")

        if warnings:
            kernel.io.warning(f"Pylint found warnings in {file_path}:")
            for warning in warnings:
                kernel.io.warning(f"Line {warning.get('line')}: {warning.get('message')} ({warning.get('symbol')})")
                kernel.io.log(warning)

        if conventions:
            kernel.io.info("Conventions:")
            for convention in conventions:
                kernel.io.base(
                    message=f"  Line {convention.get('line')}: {convention.get('message')} ({convention.get('symbol')})")

        if errors:
            return False
        else:
            if warnings:
                kernel.io.success("Pylint warnings found but no critical errors")
            else:
                kernel.io.success("No pylint issues found")
            return True
    else:
        kernel.io.success(f"Pylint check passed for {file_path}")
        return True
