import os.path
from typing import List, Set

from wexample_wex_core.middleware.each_file_middleware import EachFileMiddleware


class EachPythonFileMiddleware(EachFileMiddleware):
    """
    Middleware for processing Python files only.
    - Filters files by .py extension by default
    - Ignores special directories like __pycache__ during recursion
    """
    # Default extension to filter
    python_extension_only: bool = True
    
    # Default list of directories to ignore during recursion
    ignored_directories: Set[str] = {
        "__pycache__",
        ".git",
        ".idea",
        ".vscode",
        "venv",
        "env",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
    
    def __init__(self, **kwargs):
        # Allow overriding the default settings
        if "python_extension_only" in kwargs:
            self.python_extension_only = kwargs.pop("python_extension_only")
            
        if "ignored_directories" in kwargs:
            self.ignored_directories = set(kwargs.pop("ignored_directories"))
            
        super().__init__(**kwargs)
    
    def _should_process_item(self, item_path: str) -> bool:
        """
        Only process Python files based on extension.
        
        Args:
            item_path: Path to the item to check
            
        Returns:
            True if the item should be processed, False otherwise
        """
        # First check if it's a file (parent class behavior)
        if not os.path.isfile(item_path):
            return False
                
        # If python_extension_only is enabled, check file extension
        if self.python_extension_only:
            return item_path.endswith(".py")
            
        # Otherwise, accept all files
        return True
        
    def _process_directory_recursively(self, directory_path: str, option_name: str, current_depth: int = 0) -> List[dict]:
        """
        Override the recursive processing to skip ignored directories.
        
        Args:
            directory_path: Path to the directory to process
            option_name: Name of the option to set in function kwargs
            current_depth: Current recursion depth
            
        Returns:
            List of function kwargs dictionaries for each matching path
        """
        if current_depth > self.recursion_limit:
            return []  # Stop recursion if max depth is reached
            
        result = []
        
        try:
            # Iterate through all directory items
            for item in os.listdir(directory_path):
                # Skip ignored directories during glob expansion
                if self.recursive and item in self.ignored_directories:
                    continue
                    
                item_path = os.path.join(directory_path, item)
                
                # Process items that match the subclass criteria
                if self._should_process_item(item_path):
                    # Create a copy of arguments for each matching item
                    result.append({option_name: item_path})
                
                # If recursive is enabled and item is a directory, process it recursively
                if self.recursive and os.path.isdir(item_path):
                    subdirectory_results = self._process_directory_recursively(
                        directory_path=item_path,
                        option_name=option_name,
                        current_depth=current_depth + 1
                    )
                    result.extend(subdirectory_results)
        except (PermissionError, FileNotFoundError):
            # Skip directories we can't access
            pass
            
        return result
