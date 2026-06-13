from __future__ import annotations

import pathlib
import shutil
from pathlib import Path

import pytest


def test_apply_pdm_bin_dir_prepends_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wexample_wex_addon_dev_python.helpers.pdm import apply_pdm_bin_dir

    monkeypatch.setenv("PATH", "/usr/bin")
    apply_pdm_bin_dir("/opt/bin")

    import os

    assert os.environ["PATH"] == "/opt/bin:/usr/bin"


def test_apply_pdm_bin_dir_noop_when_already_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wexample_wex_addon_dev_python.helpers.pdm import apply_pdm_bin_dir

    monkeypatch.setenv("PATH", "/opt/bin:/usr/bin")
    apply_pdm_bin_dir("/opt/bin")

    import os

    assert os.environ["PATH"] == "/opt/bin:/usr/bin"


def test_detect_pdm_bin_dir_returns_none_when_pdm_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wexample_wex_addon_dev_python.helpers.pdm import detect_pdm_bin_dir

    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/pdm")

    assert detect_pdm_bin_dir() is None


def test_detect_pdm_bin_dir_returns_local_bin_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from wexample_wex_addon_dev_python.helpers.pdm import detect_pdm_bin_dir

    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    local_bin = tmp_path / ".local" / "bin"
    local_bin.mkdir(parents=True)
    (local_bin / "pdm").write_text("#!/bin/sh\n")

    assert detect_pdm_bin_dir() == str(local_bin)


def test_detect_pdm_bin_dir_returns_none_when_nowhere(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from wexample_wex_addon_dev_python.helpers.pdm import detect_pdm_bin_dir

    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))

    assert detect_pdm_bin_dir() is None
