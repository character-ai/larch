"""Focused contracts for the retired small /design session wrappers."""

from __future__ import annotations

from pathlib import Path

from larch.design import design_session
from larch.review import plan_review
from larch.review import plan_review_loop

from test_support import make_design_tmpdir, write_design_source_env


def _session_args(path: Path, *, pid: str = "12345") -> list[str]:
    return ["--session-env-path", str(path), "--claude-pid", pid]


def _source_env(tmpdir: Path, *, plugin_root: Path) -> Path:
    return write_design_source_env(
        tmpdir,
        overrides={"CLAUDE_PLUGIN_ROOT": str(plugin_root), "ISSUE_NUMBER": "7483"},
    )


def test_small_entries_rehydrate_normal_session_env_and_preview_once(tmp_path: Path, monkeypatch) -> None:
    design = make_design_tmpdir(tmp_path)
    source = _source_env(design, plugin_root=Path.cwd())
    _ = (design / "plan.txt").write_text("# Plan\n", encoding="utf-8")
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)

    assert design_session.prelude_main(_session_args(source)) == 0
    assert plan_review.step3_entry_preview_main(_session_args(source)) == 0
    assert (design / ".step3-entry-plan-printed").is_file()
    assert plan_review.step3_entry_preview_main(_session_args(source)) == 0


def test_small_entries_refuse_invalid_session_pid_for_symlink(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    sessions = home / ".cache" / "larch" / "sessions"
    sessions.mkdir(parents=True)
    design = make_design_tmpdir(tmp_path)
    source = _source_env(design, plugin_root=Path.cwd())
    swapped = sessions / "current-design-env-99999.sh"
    swapped.symlink_to(source)
    monkeypatch.setenv("HOME", str(home))

    assert plan_review.step3_entry_preview_main(_session_args(swapped)) != 0
    assert plan_review.step3_entry_state_main(_session_args(swapped)) != 0


def test_small_entries_pause_before_state_or_preview(tmp_path: Path, monkeypatch) -> None:
    design = make_design_tmpdir(tmp_path)
    source = _source_env(design, plugin_root=Path.cwd())
    (design / ".pause-requested").touch()
    calls: list[Path] = []

    def fake_pause_save(argv: list[str]) -> int:
        calls.append(Path(argv[1]))
        return 0

    monkeypatch.setattr(design_session.design_pause, "pause_save_main", fake_pause_save)
    assert design_session.prelude_main(_session_args(source)) == 0
    assert plan_review.step3_entry_preview_main(_session_args(source)) == 0
    assert plan_review.step3_entry_state_main(_session_args(source)) == 0
    assert plan_review.step3_gate_b_bypass_main(_session_args(source)) == 0
    assert calls == [design, design, design, design]


def test_continuation_and_bypass_reject_missing_tmpdir(monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path.cwd()))
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)

    assert design_session.step3_continuation_entry_main([]) == 1
    assert plan_review.step3_gate_b_bypass_main([]) == 1


def test_missing_tmpdir_preview_never_reads_a_cwd_pause_marker(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pause-requested").touch()
    assert plan_review.step3_entry_preview_main([]) == 0


def test_continuation_rejects_disallowed_tmpdir(monkeypatch) -> None:
    disallowed = Path.cwd() / ".test-7483-disallowed"
    disallowed.mkdir(exist_ok=True)
    source = disallowed / "source-env.sh"
    _ = source.write_text(
        f"export DESIGN_TMPDIR={disallowed}\nexport CLAUDE_PLUGIN_ROOT={Path.cwd()}\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    try:
        assert design_session.step3_continuation_entry_main(_session_args(source)) == 2
    finally:
        source.unlink(missing_ok=True)
        disallowed.rmdir()


def test_gate_b_bypass_preserves_step35_short_circuit(tmp_path: Path, monkeypatch) -> None:
    design = make_design_tmpdir(tmp_path)
    source = _source_env(design, plugin_root=Path.cwd())
    (design / ".completed").mkdir()
    (design / ".completed" / "step-3.5").touch()
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)

    assert plan_review.step3_gate_b_bypass_main(_session_args(source)) == 0


def test_preview_child_failure_propagates(tmp_path: Path, monkeypatch) -> None:
    design = make_design_tmpdir(tmp_path)
    source = _source_env(design, plugin_root=Path.cwd())
    monkeypatch.setattr(plan_review_loop, "emit_design_plan_preview", lambda _argv: 9)

    assert plan_review.step3_entry_preview_main(_session_args(source)) == 9


def test_preview_malformed_child_output_does_not_write_sentinel(tmp_path: Path, monkeypatch) -> None:
    design = make_design_tmpdir(tmp_path)
    source = _source_env(design, plugin_root=Path.cwd())

    def emit_malformed(_argv: list[str]) -> int:
        print("unexpected preview payload")
        return 0

    monkeypatch.setattr(plan_review_loop, "emit_design_plan_preview", emit_malformed)
    assert plan_review.step3_entry_preview_main(_session_args(source)) == 0
    assert not (design / ".step3-entry-plan-printed").exists()


def test_reentry_state_is_owned_by_retained_step3_entry(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    _ = (design / "issue-body.txt").write_text("scope\n", encoding="utf-8")
    assert plan_review.step3_entry(["--design-tmpdir", str(design), "--reentry"]) == 0
    assert (design / ".step3-reentry").is_file()
