from __future__ import annotations

from pathlib import Path

import pytest

from larch.lint.lint_readability_preamble import main

EXTERNAL = "Style requirements: `<READABILITY_STYLE>`."
PLAN_REVIEW = "Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`."
ORCH = "**MANDATORY — READ ENTIRE FILE before composing fixture text: `skills/design/references/readability-style.md`.**"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def manifest(root: Path, rows: str) -> None:
    write(root / "scripts/lint-readability-preamble.tsv", rows)


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_valid_external_and_orchestrator(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest(
        tmp_path,
        "skills/design/references/a.md\texternal-prompt\t1\tstandard\t\nskills/design/SKILL.md\torchestrator-inline\t2\t\t2b,3b\n",
    )
    write(tmp_path / "skills/design/references/a.md", EXTERNAL + "\n")
    write(tmp_path / "skills/design/SKILL.md", f"<!-- step:2b fixture -->\n{ORCH}\n<!-- step:3b fixture -->\n{ORCH}\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


@pytest.mark.parametrize(("kind", "line"), [("plan-review", PLAN_REVIEW)])
def test_prompt_kinds(tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str, line: str) -> None:
    manifest(tmp_path, f"prompt.md\texternal-prompt\t1\t{kind}\t\n")
    write(tmp_path / "prompt.md", line + "\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


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
    write(tmp_path / "skills/design/SKILL.md", f"<!-- step:2b fixture -->\n{ORCH}\n<!-- step:3b fixture -->\nno directive\n{ORCH}\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
    manifest(tmp_path, "skills/design/SKILL.md\torchestrator-inline\t1\t\t2b,3b\n")
    write(tmp_path / "skills/design/SKILL.md", f"<!-- step:2b fixture -->\n{ORCH}\n<!-- step:3b fixture -->\nmissing\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert 'step "3b": expected >=1 orchestrator-inline readability-style directive' in err


def test_manifest_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(tmp_path)]) == 2
    assert "manifest not found" in capsys.readouterr().err
    manifest(tmp_path, "broken.md\texternal-prompt\t\tstandard\t\n")
    assert main(["--root", str(tmp_path)]) == 2
    assert "invalid expected_count" in capsys.readouterr().err
