from __future__ import annotations


def detect_pdm_bin_dir() -> str | None:
    import pathlib
    import shutil

    if shutil.which("pdm"):
        return None
    local_bin = pathlib.Path.home() / ".local" / "bin"
    if (local_bin / "pdm").is_file():
        return str(local_bin)
    return None


def apply_pdm_bin_dir(value: str) -> None:
    import os

    if value not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{value}:{os.environ.get('PATH', '')}"
