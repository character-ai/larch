# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnusedCallResult=false
"""Fixture-level parity checks for the duplicate-code runner."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import duplicate_code
import duplicate_code_parity


def _write_rc(root: Path, *, min_lines: int = 4) -> Path:
    rcfile = root / ".pylintrc"
    rcfile.write_text(
        f"""
[MESSAGES CONTROL]
disable=all

[REPORTS]
reports=no
score=no

[MAIN]
persistent=no

[SIMILARITIES]
min-similarity-lines={min_lines}
ignore-comments=yes
ignore-docstrings=yes
ignore-imports=yes
ignore-signatures=yes
""".lstrip(),
        encoding="utf-8",
    )
    return rcfile


def _module(lines: int) -> str:
    return "\n".join(f"VALUE_{index} = {index}" for index in range(lines)) + "\n"


def test_legacy_pylint_and_new_runner_agree_on_exit_code_for_fixture(tmp_path: Path) -> None:
    rcfile = _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text(_module(5), encoding="utf-8")

    duplicate_code_parity.assert_parity(tmp_path, rcfile)


def test_digest_mismatch_blocks_even_when_exit_codes_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rcfile = _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text(_module(5), encoding="utf-8")

    result = duplicate_code_parity.run_parity(tmp_path, rcfile)
    normalized_legacy = duplicate_code_parity.parity_exit_code(result.legacy_exit, legacy=True)
    assert normalized_legacy == result.new_exit == 1
    assert result.new_digest != "[]"

    def wrong_legacy_digest(_root: Path, _rcfile: Path) -> str:
        return "[]"

    monkeypatch.setattr(duplicate_code_parity, "legacy_cluster_digest", wrong_legacy_digest)

    with pytest.raises(AssertionError, match="digest mismatch"):
        duplicate_code_parity.assert_parity(tmp_path, rcfile)


def test_cli_digest_matches_internal_digest(tmp_path: Path) -> None:
    rcfile = _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text(_module(5), encoding="utf-8")
    internal = duplicate_code.run_duplicate_code(root=tmp_path, rcfile=rcfile, jobs=1).digest

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("cli.py")),
            "lint",
            "duplicate-code",
            "--root",
            str(tmp_path),
            "--rcfile",
            str(rcfile),
            "--jobs",
            "1",
            "--emit-cluster-digest",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout.strip() == internal


@pytest.mark.skipif(
    os.environ.get("LARCH_DUPLICATE_CODE_FULL_TREE_PARITY") != "1",
    reason="full-tree legacy/new parity is opt-in via LARCH_DUPLICATE_CODE_FULL_TREE_PARITY=1",
)
def test_full_python_tree_legacy_new_parity() -> None:
    root = Path(__file__).resolve().parent
    rcfile = root / ".pylintrc"
    duplicate_code_parity.assert_parity(root, rcfile)
