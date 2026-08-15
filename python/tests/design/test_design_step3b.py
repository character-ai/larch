"""Regression coverage for the in-process Step 3b entry boundary."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from larch.design import design_dialectic, design_step3b

from test_support import make_design_tmpdir, write_design_source_env


def _args(tmpdir: Path, *, plugin_root: Path) -> list[str]:
    source = write_design_source_env(
        tmpdir,
        overrides={"CLAUDE_PLUGIN_ROOT": str(plugin_root), "ISSUE_NUMBER": "7485"},
    )
    return ["--session-env-path", str(source), "--claude-pid", "7485"]


def _probe(value: str, *, rc: int = 0) -> Callable[[Sequence[str]], int]:
    def fake_probe(_argv: Sequence[str]) -> int:
        if value:
            print(value)
        return rc

    return fake_probe


def _finalize(rc: int) -> Callable[..., subprocess.CompletedProcess[str]]:
    def fake_finalize(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, rc, stdout="", stderr="")

    return fake_finalize


@pytest.mark.parametrize(("probe", "expected"), [("DIALECTIC_GATEC_DEBATE_REQUIRED=false", "foreground"), ("DIALECTIC_GATEC_DEBATE_REQUIRED=true", "background")])
def test_finalize_maps_every_probe_value_and_writes_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], probe: str, expected: str,
) -> None:
    design = make_design_tmpdir(tmp_path)
    args = _args(design, plugin_root=Path.cwd())
    monkeypatch.setattr(design_step3b.subprocess, "run", _finalize(0))
    monkeypatch.setattr(design_dialectic, "gatec_main", _probe(probe))

    assert design_step3b.step3b_entry_main([*args, "--mode", "finalize"]) == 0
    assert capsys.readouterr().out == f"STEP4_MODE={expected}\n"
    assert (design / ".step4-mode.env").read_text(encoding="utf-8") == f"STEP4_MODE={expected}\n"
    assert (design / ".completed" / "step-3.5").is_file()
    assert (design / ".completed" / "step-3b").is_file()


@pytest.mark.parametrize(
    "probe",
    ["", "DIALECTIC_GATEC_DEBATE_REQUIRED=maybe", "DIALECTIC_GATEC_DEBATE_REQUIRED=true\nDIALECTIC_GATEC_DEBATE_REQUIRED=false"],
)
def test_finalize_rejects_missing_duplicate_or_malformed_probe_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], probe: str,
) -> None:
    design = make_design_tmpdir(tmp_path)
    monkeypatch.setattr(design_step3b.subprocess, "run", _finalize(0))
    monkeypatch.setattr(design_dialectic, "gatec_main", _probe(probe))

    assert design_step3b.step3b_entry_main([*_args(design, plugin_root=Path.cwd()), "--mode", "finalize"]) == 1
    assert "did not emit exactly one valid debate-required row" in capsys.readouterr().err
    assert not (design / ".completed" / "step-3b").exists()


def test_finalize_preserves_child_failure_and_does_not_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    design = make_design_tmpdir(tmp_path)
    monkeypatch.setattr(design_step3b.subprocess, "run", _finalize(7))

    assert design_step3b.step3b_entry_main([*_args(design, plugin_root=Path.cwd()), "--mode", "finalize"]) == 7
    assert "FINALIZE failed" in capsys.readouterr().err
    assert not (design / ".completed" / "step-3b").exists()


def test_finalize_probe_failure_keeps_diagnostics_and_does_not_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    design = make_design_tmpdir(tmp_path)
    monkeypatch.setattr(design_step3b.subprocess, "run", _finalize(0))
    monkeypatch.setattr(design_dialectic, "gatec_main", _probe("probe failure", rc=9))

    assert design_step3b.step3b_entry_main([*_args(design, plugin_root=Path.cwd()), "--mode", "finalize"]) == 9
    assert "dialectic Gate C probe failed" in capsys.readouterr().err
    assert not (design / ".completed" / "step-3b").exists()


def test_finalize_fresh_entry_replaces_stale_resume_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = make_design_tmpdir(tmp_path)
    completed = design / ".completed"
    completed.mkdir()
    _ = (completed / "step-3b").touch()
    _ = (design / ".step4-mode.env").write_text("STEP4_MODE=background\n", encoding="utf-8")
    monkeypatch.setattr(design_step3b.subprocess, "run", _finalize(0))
    monkeypatch.setattr(design_dialectic, "gatec_main", _probe("DIALECTIC_GATEC_DEBATE_REQUIRED=false"))

    assert design_step3b.step3b_entry_main([*_args(design, plugin_root=Path.cwd()), "--mode", "entry"]) == 0
    assert (design / ".step4-mode.env").read_text(encoding="utf-8") == "STEP4_MODE=foreground\n"


def test_diagram_required_clears_stale_artifacts_without_completion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    design = make_design_tmpdir(tmp_path)
    completed = design / ".completed"
    completed.mkdir()
    _ = (completed / "step-4").touch()
    _ = (completed / "step-5b").touch()
    _ = (design / "plan.txt").write_text("### UPDATED: python/larch/design/design_step3b.py\n", encoding="utf-8")
    for name in ("architecture-diagram.md", "architecture-diagram.candidate.md", "architecture-diagram.skipped", "architecture-diagram-generation.failure.log", "architecture-diagram-sanitizer.failure.log"):
        _ = (design / name).touch()

    assert design_step3b.step3b_entry_main([*_args(design, plugin_root=Path.cwd()), "--mode", "diagram"]) == 0
    assert capsys.readouterr().out == "DIAGRAM_REQUIRED=true\n"
    assert not any((design / name).exists() for name in ("architecture-diagram.md", "architecture-diagram.candidate.md", "architecture-diagram.skipped", "architecture-diagram-generation.failure.log", "architecture-diagram-sanitizer.failure.log"))
    assert not (completed / "step-5b.5").exists()


def test_diagram_skip_writes_only_skip_completion_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    design = make_design_tmpdir(tmp_path)
    completed = design / ".completed"
    completed.mkdir()
    _ = (completed / "step-4").touch()
    _ = (completed / "step-5b").touch()
    _ = (design / "plan.txt").write_text("### MAY_UPDATE: docs/guide.md\n", encoding="utf-8")
    _ = (design / "architecture-diagram.md").touch()
    _ = (design / "architecture-diagram.candidate.md").touch()

    assert design_step3b.step3b_entry_main([*_args(design, plugin_root=Path.cwd()), "--mode", "diagram"]) == 0
    assert capsys.readouterr().out.startswith("DIAGRAM_REQUIRED=false\n")
    assert (design / "architecture-diagram.skipped").is_file()
    assert (completed / "step-5b.5").is_file()
    assert not (design / "architecture-diagram.md").exists()
    assert not (design / "architecture-diagram.candidate.md").exists()


@pytest.mark.parametrize("mode", ["", "unexpected"])
def test_unknown_or_missing_mode_uses_usage_exit_code(capsys: pytest.CaptureFixture[str], mode: str) -> None:
    argv = [] if not mode else ["--mode", mode]
    assert design_step3b.step3b_entry_main(argv) == 2
    assert "--mode finalize|diagram required" in capsys.readouterr().err
