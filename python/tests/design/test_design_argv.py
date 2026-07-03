"""Tests for the Python /design argv CLI bridge."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


CLI = Path(__file__).resolve().parents[2] / "cli.py"


def _run_parse(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "design", "parse-flags", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _stdout_kvs(stdout: str) -> dict[str, str]:
    kvs: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        kvs[key] = val
    return kvs


def test_design_parse_flags_cli_stdout_uses_legacy_uppercase_kvs() -> None:
    result = _run_parse("--brainstorm", "123")
    assert result.returncode == 0
    kvs = _stdout_kvs(result.stdout)
    assert kvs["BRAINSTORM_REQUESTED"] == "true"
    assert kvs["PARTITION_REQUESTED"] == "false"
    assert kvs["POSITIONAL_KIND"] == "issue"
    assert kvs["POSITIONAL_VALUE"] == "123"
    assert "brainstorm_requested=" not in result.stdout


def test_design_parse_flags_cli_writes_sourceable_output(tmp_path: Path) -> None:
    output = tmp_path / "argv.env"
    result = _run_parse("--output", str(output), "--brainstorm", "123")
    assert result.returncode == 0
    text = output.read_text(encoding="utf-8")
    assert "brainstorm_requested='true'" in text
    assert "POSITIONAL_KIND='issue'" in text
    assert "POSITIONAL_VALUE='123'" in text


@pytest.mark.parametrize(
    ("args", "error_token"),
    [
        (("--hard",), "--hard"),
        (("--bogus",), "--bogus"),
        # Forbidden/unknown flags after a numeric issue positional still error
        # (non-contiguous argv is parsed, not silently dropped).
        (("123", "--hard"), "--hard"),
        (("123", "--bogus"), "--bogus"),
        (("--run-id",), "--run-id"),
        (("--per-round-approval", "--per-round-approval"), "--per-round-approval"),
        (("--skip-approve", "--skip-approve"), "--skip-approve"),
        (("-s", "-s"), "--skip-approve"),
        (("--run-id", "bad\nid", "3249"), "newline-in-value"),
        (("123", "--run-id", "--bogus"), "--bogus"),
        (("123", "--run-id", "--hard"), "--hard"),
        (("123", "--run-id", "--brainstorm"), "--brainstorm"),
        (("foo\n=true",), "newline-in-value"),
    ],
)
def test_design_parse_flags_cli_rejections(args: tuple[str, ...], error_token: str) -> None:
    result = _run_parse(*args)
    assert result.returncode == 3
    kvs = _stdout_kvs(result.stdout)
    assert kvs["VALIDATION_ERROR"] == error_token
    assert kvs["ERROR_MESSAGE"] == f"**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.** {error_token}"
    assert "PARTITION_REQUESTED" not in kvs


@pytest.mark.parametrize(
    "args",
    [
        ("--output", "public-path"),
        ("3249", "--output", "public-path"),
    ],
)
def test_design_parse_flags_cli_rejects_public_output_flag(
    tmp_path: Path,
    args: tuple[str, ...],
) -> None:
    output = tmp_path / "argv.env"
    result = _run_parse("--output", str(output), *args)
    assert result.returncode == 3
    kvs = _stdout_kvs(result.stdout)
    assert kvs["VALIDATION_ERROR"] == "--output"
    assert kvs["ERROR_MESSAGE"] == "**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.** --output"
    text = output.read_text(encoding="utf-8")
    assert "VALIDATION_ERROR='--output'" in text
    assert "ERROR_MESSAGE='**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.** --output'" in text
    assert "partition_requested=" not in text


def test_design_parse_flags_cli_metacharacters_preserved_with_output(tmp_path: Path) -> None:
    output = tmp_path / "argv.env"
    result = _run_parse("--output", str(output), "Strunk & White $x")
    assert result.returncode == 0
    kvs = _stdout_kvs(result.stdout)
    assert kvs["POSITIONAL_KIND"] == "verbal"
    assert kvs["POSITIONAL_VALUE"] == "Strunk & White $x"
    text = output.read_text(encoding="utf-8")
    assert "POSITIONAL_VALUE='Strunk & White $x'" in text


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("123", "--no-dedup"), {"NO_DEDUP_REQUESTED": "true"}),
        (("123", "--skip-approve"), {"SKIP_APPROVE_REQUESTED": "true"}),
        (("123", "-p"), {"PARTITION_REQUESTED": "true"}),
        (("123", "--run-id", "abc"), {"RUN_ID": "abc"}),
        # Flags on both sides of the issue id (non-contiguous argv).
        (
            ("--brainstorm", "123", "--no-dedup"),
            {"BRAINSTORM_REQUESTED": "true", "NO_DEDUP_REQUESTED": "true"},
        ),
    ],
)
def test_design_parse_flags_cli_honors_flags_after_issue(
    args: tuple[str, ...],
    expected: dict[str, str],
) -> None:
    result = _run_parse(*args)
    assert result.returncode == 0
    kvs = _stdout_kvs(result.stdout)
    assert kvs["POSITIONAL_KIND"] == "issue"
    assert kvs["POSITIONAL_VALUE"] == "123"
    for key, val in expected.items():
        assert kvs[key] == val


def test_design_parse_flags_cli_ignores_extra_nonflag_token_after_issue() -> None:
    result = _run_parse("123", "456")
    assert result.returncode == 0
    kvs = _stdout_kvs(result.stdout)
    assert kvs["POSITIONAL_KIND"] == "issue"
    assert kvs["POSITIONAL_VALUE"] == "123"


def test_design_parse_flags_cli_verbal_tail_keeps_flag_like_tokens_literal() -> None:
    result = _run_parse("feature", "--no-dedup")
    assert result.returncode == 0
    kvs = _stdout_kvs(result.stdout)
    assert kvs["POSITIONAL_KIND"] == "verbal"
    assert kvs["POSITIONAL_VALUE"] == "feature --no-dedup"
    assert kvs["NO_DEDUP_REQUESTED"] == "false"


def test_design_parse_argv_cli_is_not_registered() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "design", "parse-argv", "--brainstorm", "123"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
