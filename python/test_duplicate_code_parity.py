# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnusedCallResult=false
"""Fixture-level parity checks for the duplicate-code runner."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duplicate_code


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


def _legacy_exit(root: Path, rcfile: Path) -> int:
    result = subprocess.run(
        [
            "pylint",
            "--rcfile",
            str(rcfile),
            "--disable=all",
            "--enable=duplicate-code",
            "--persistent=no",
            "-j",
            "1",
            ".",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return 1 if result.returncode else 0


def _new_exit_and_digest(root: Path, rcfile: Path) -> tuple[int, str]:
    result = duplicate_code.run_duplicate_code(root=root, rcfile=rcfile, jobs=1)
    return result.exit_code, result.digest


def test_legacy_pylint_and_new_runner_agree_on_exit_code_for_fixture(tmp_path: Path) -> None:
    rcfile = _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text(_module(5), encoding="utf-8")

    legacy_rc = _legacy_exit(tmp_path, rcfile)
    new_rc, digest = _new_exit_and_digest(tmp_path, rcfile)

    assert legacy_rc == new_rc == 1
    assert digest != "[]"


def test_digest_mismatch_blocks_even_when_exit_codes_match(tmp_path: Path) -> None:
    rcfile = _write_rc(tmp_path, min_lines=4)
    (tmp_path / "a.py").write_text(_module(5), encoding="utf-8")
    (tmp_path / "b.py").write_text(_module(5), encoding="utf-8")

    legacy_rc = 1
    new_rc, digest = _new_exit_and_digest(tmp_path, rcfile)
    wrong_digest = "[]"

    assert legacy_rc == new_rc == 1
    assert digest != wrong_digest


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
