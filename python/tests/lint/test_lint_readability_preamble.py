from __future__ import annotations

from pathlib import Path

import pytest

from larch.lint.lint_readability_preamble import main

EXTERNAL = "Style requirements: `<READABILITY_STYLE>`."
PLAN_REVIEW = "Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`."
PUBLIC_PATH = "${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md"
DEV_PATH = "$PWD/skills/shared/readability-style.md"
PUBLIC_ORCH = "**MANDATORY: READ ENTIRE FILE before composing fixture text: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**"
DEV_ORCH = "**MANDATORY: READ ENTIRE FILE before composing fixture text: `$PWD/skills/shared/readability-style.md`.**"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def manifest(root: Path, rows: str) -> None:
    write(root / "scripts/lint-readability-preamble.tsv", rows)


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_valid_external_orchestrator_and_skill_coverage(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(
        tmp_path,
        "__metadata__\tmetadata-min-count\t3\t\t\n"
        "skills/design/references/a.md\texternal-prompt\t1\tstandard\t\n"
        "skills/design/SKILL.md\torchestrator-inline\t2\t\t2b,3b\n",
    )
    write(tmp_path / "skills/design/references/a.md", EXTERNAL + "\n")
    write(
        tmp_path / "skills/design/SKILL.md",
        f"<!-- step:2b fixture -->\n{PUBLIC_ORCH}\n<!-- step:3b fixture -->\n{PUBLIC_ORCH}\n",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


@pytest.mark.parametrize(("kind", "line"), [("plan-review", PLAN_REVIEW)])
def test_prompt_kinds(tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str, line: str) -> None:
    manifest(tmp_path, f"prompt.md\texternal-prompt\t1\t{kind}\t\n")
    write(tmp_path / "prompt.md", line + "\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err




def test_em_dash_mandatory_directive_does_not_count(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    legacy = PUBLIC_ORCH.replace("MANDATORY:", f"MANDATORY {chr(0x2014)}")
    manifest(tmp_path, "skills/foo/SKILL.md\torchestrator-inline\t1\t\t\n")
    write(tmp_path / "skills/foo/SKILL.md", legacy + "\n")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/foo/SKILL.md: expected 1 orchestrator-inline readability-style directives, found 0" in err

def test_missing_external_reports_count(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "prompt.md\texternal-prompt\t2\tstandard\t\n")
    write(tmp_path / "prompt.md", EXTERNAL + "\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "prompt.md: expected 2 external-prompt readability-style directives, found 1" in err


def test_missing_file_reports_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "missing.md\texternal-prompt\t1\tstandard\t\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "missing.md: missing external-prompt readability-style directive" in err


def test_step_placement(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "skills/design/SKILL.md\torchestrator-inline\t2\t\t2b,3b\n")
    write(
        tmp_path / "skills/design/SKILL.md",
        f"<!-- step:2b fixture -->\n{PUBLIC_ORCH}\n<!-- step:3b fixture -->\nno directive\n{PUBLIC_ORCH}\n",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
    manifest(tmp_path, "skills/design/SKILL.md\torchestrator-inline\t1\t\t2b,3b\n")
    write(tmp_path / "skills/design/SKILL.md", f"<!-- step:2b fixture -->\n{PUBLIC_ORCH}\n<!-- step:3b fixture -->\nmissing\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert 'step "3b": expected >=1 orchestrator-inline readability-style directive' in err


def test_floor_pass_and_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t1\t\t\nprompt.md\texternal-prompt\t1\tstandard\t\n")
    write(tmp_path / "prompt.md", EXTERNAL + "\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t2\t\t\nprompt.md\texternal-prompt\t1\tstandard\t\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "expected_count floor 2 exceeds manifest total 1" in err


def test_public_skill_path_form(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "skills/foo/SKILL.md\torchestrator-inline\t1\t\t\n")
    write(tmp_path / "skills/foo/SKILL.md", DEV_ORCH + "\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/foo/SKILL.md: expected 1 orchestrator-inline readability-style directives, found 0" in err
    assert "skills/foo/SKILL.md: missing per-skill readability directive" in err
    assert "skills/foo/SKILL.md: uses wrong readability directive path form" in err


def test_dev_only_skill_path_form(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, ".claude/skills/foo/SKILL.md\torchestrator-inline\t1\t\t\n")
    write(tmp_path / ".claude/skills/foo/SKILL.md", PUBLIC_ORCH + "\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert ".claude/skills/foo/SKILL.md: expected 1 orchestrator-inline readability-style directives, found 0" in err
    assert ".claude/skills/foo/SKILL.md: missing per-skill readability directive" in err
    assert ".claude/skills/foo/SKILL.md: uses wrong readability directive path form" in err


def test_missing_per_skill_directive(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t0\t\t\n")
    write(tmp_path / "skills/foo/SKILL.md", "# Foo\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/foo/SKILL.md: missing per-skill readability directive" in err


def test_missing_agent_directive(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t0\t\t\n")
    write(tmp_path / "agents/code-reviewer.md", "# Agent\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "agents/code-reviewer.md: missing reviewer readability directive" in err


def test_agent_directive_present(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t0\t\t\n")
    write(tmp_path / "agents/code-reviewer.md", PUBLIC_ORCH + "\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_agent_wrong_path_form(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t0\t\t\n")
    write(tmp_path / "agents/reviewer-foo.md", DEV_ORCH + "\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "agents/reviewer-foo.md: missing reviewer readability directive" in err
    assert "agents/reviewer-foo.md: uses wrong readability directive path form" in err


def test_non_reviewer_agent_not_checked(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t0\t\t\n")
    write(tmp_path / "agents/codex-implementer.md", "# Agent\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_bare_path_mention_does_not_count_as_directive(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t0\t\t\n")
    write(tmp_path / "skills/foo/SKILL.md", f"See {PUBLIC_PATH} for the style rules.\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/foo/SKILL.md: missing per-skill readability directive" in err


def test_backticked_path_mention_does_not_count_as_directive(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t0\t\t\n")
    write(tmp_path / "skills/foo/SKILL.md", f"See `{PUBLIC_PATH}` for the style rules.\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/foo/SKILL.md: missing per-skill readability directive" in err


def test_non_mandatory_path_mention_does_not_count_as_directive(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "__metadata__\tmetadata-min-count\t0\t\t\n")
    write(tmp_path / ".claude/skills/foo/SKILL.md", f"Read {DEV_PATH} before writing prose.\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert ".claude/skills/foo/SKILL.md: missing per-skill readability directive" in err


def test_explicit_exemption_behavior(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(tmp_path, "skills/foo/SKILL.md\tskill-exempt\t0\tpure pass-through\t\n")
    write(tmp_path / "skills/foo/SKILL.md", "# Foo\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_invalid_manifest_metadata_or_exemption_rows(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(tmp_path)]) == 2
    assert "manifest not found" in capsys.readouterr().err
    manifest(tmp_path, "broken.md\texternal-prompt\t\tstandard\t\n")
    assert main(["--root", str(tmp_path)]) == 2
    assert "invalid expected_count" in capsys.readouterr().err
    manifest(tmp_path, "skills/foo/SKILL.md\tskill-exempt\t1\t\t\n")
    assert main(["--root", str(tmp_path)]) == 2
    assert "invalid skill exemption row" in capsys.readouterr().err
    manifest(tmp_path, "a\tmetadata-min-count\t0\t\t\nb\tmetadata-min-count\t0\t\t\n")
    assert main(["--root", str(tmp_path)]) == 1
    assert "duplicate metadata-min-count rows" in capsys.readouterr().err
