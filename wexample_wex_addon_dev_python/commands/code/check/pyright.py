from wexample_wex_core.common.kernel import Kernel


def _code_check_pyright(kernel: "Kernel", file_path: str) -> bool:
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
    process = subprocess.run(cmd, capture_output=True, text=True)
    
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
    
    try:
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
                kernel.io.error(f"Pyright found errors in {file_path}:")
                for error in errors:
                    line = error.get("range", {}).get("start", {}).get("line", 0) + 1
                    message = error.get("message", "Unknown error")
                    rule = error.get("rule", "")
                    rule_text = f" ({rule})" if rule else ""
                    kernel.io.base(message=f"  Line {line}: {message}{rule_text}")
            
            # Display warnings
            if warnings:
                kernel.io.warning(f"Pyright found warnings in {file_path}:")
                for warning in warnings:
                    line = warning.get("range", {}).get("start", {}).get("line", 0) + 1
                    message = warning.get("message", "Unknown warning")
                    rule = warning.get("rule", "")
                    rule_text = f" ({rule})" if rule else ""
                    kernel.io.warning(f"Line {line}: {message}{rule_text}")
                    kernel.io.log(warning)
            
            # Display information
            if info:
                kernel.io.info("Information:")
                for item in info:
                    line = item.get("range", {}).get("start", {}).get("line", 0) + 1
                    message = item.get("message", "Unknown info")
                    rule = item.get("rule", "")
                    rule_text = f" ({rule})" if rule else ""
                    kernel.io.base(message=f"  Line {line}: {message}{rule_text}")
            
            # Only consider errors as failures
            if errors:
                return False
            else:
                if warnings:
                    kernel.io.success("Pyright warnings found but no critical errors")
                else:
                    kernel.io.success("No pyright issues found")
                return True
        else:
            kernel.io.success(f"Pyright check passed for {file_path}")
            return True
            
    except json.JSONDecodeError:
        kernel.io.error(f"Failed to parse pyright output for {file_path}")
        kernel.io.error(f"Raw output: {json_output[:200]}...")
        return False
    except Exception as e:
        kernel.io.error(f"Unexpected error during pyright check: {e}")
        import traceback
        traceback.print_exc()
        return False
