from wexample_wex_core.common.kernel import Kernel


def _code_check_mypy(kernel: "Kernel", file_path: str) -> bool:
    """Check a Python file using mypy for static type checking.

    Args:
        kernel: The application kernel
        file_path: Path to the Python file to check

    Returns:
        bool: True if check passes, False otherwise
    """
    import sys

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

    return False
