from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint.lint_skill_md_flag_signature import main

if TYPE_CHECKING:
    import pytest


def write_script(path: Path, *flags: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    arms = "".join(f"    --{flag})\n      shift 2\n      ;;\n" for flag in flags)
    _ = path.write_text(f'#!/usr/bin/env bash\nwhile [ "$#" -gt 0 ]; do\n  case "$1" in\n{arms}    *) exit 2 ;;\n  esac\ndone\n', encoding="utf-8")


def write_skill(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(body, encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_known_flag_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_script(tmp_path / "scripts/example.sh", "known-flag")
    write_skill(tmp_path, "skills/design/SKILL.md", "```bash\n${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --known-flag value\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_unknown_flag_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_script(tmp_path / "scripts/example.sh", "known-flag")
    write_skill(tmp_path, "skills/design/SKILL.md", "```bash\n${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --unknown-flag value\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/design/SKILL.md:2: invocation uses --unknown-flag but scripts/example.sh does not declare it" in err


def test_multiline_continuation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_script(tmp_path / "scripts/example-commit.sh", "message", "only")
    write_skill(
        tmp_path,
        "skills/design/SKILL.md",
        "```bash\n${CLAUDE_PLUGIN_ROOT}/scripts/example-commit.sh \\\n  --message x \\\n  --unknown y \\\n  --only z\n```\n",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "--unknown" in err


def test_pragma_and_missing_target_warn(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_script(tmp_path / "scripts/example.sh", "known-flag")
    write_skill(
        tmp_path,
        "skills/design/SKILL.md",
        "```bash\n${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --unknown-flag value # lint-skill-md-flag-signature: ok fixture\n```\n\n```bash\n${CLAUDE_PLUGIN_ROOT}/scripts/missing.sh --dynamic value\n```\n",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0
    assert "WARN target script not found: scripts/missing.sh" in err


def test_depth_two_only_and_missing_root_exit_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_script(tmp_path / "scripts/example.sh", "known-flag")
    write_skill(tmp_path, "skills/design/nested/SKILL.md", "```bash\n${CLAUDE_PLUGIN_ROOT}/scripts/example.sh --unknown-flag value\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
    missing_rc = main(["--root", str(tmp_path / "missing")])
    assert missing_rc == 0
