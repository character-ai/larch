# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import os

import dirty_tree


def test_scope_marker_present_heading() -> None:
    text = "### FINDING_1: [important] [SCOPE-REDUCTION] trim scope\nbody\n"
    assert dirty_tree.has_scope_reduction_marker(text)


def test_scope_marker_ignores_inline_code() -> None:
    assert not dirty_tree.has_scope_reduction_marker("what: `[SCOPE-REDUCTION] nope`\n")


def test_scope_marker_present_concern_after_severity() -> None:
    text = "- **Concern**: [latent] [SCOPE-REDUCTION] trims reviewed scope\n"
    assert dirty_tree.has_scope_reduction_marker(text)


def test_scope_marker_present_what_field() -> None:
    text = "what: [SCOPE-REDUCTION] scope changed\n"
    assert dirty_tree.has_scope_reduction_marker(text)


def test_scope_check_all_in_scope(tmp_path, capsys) -> None:
    plan = tmp_path / "plan.txt"
    paths = tmp_path / "paths.z"
    plan.write_text("## Files to modify\n\n### UPDATED: `python/dirty_tree.py`\n", encoding="utf-8")
    paths.write_bytes(b"python/dirty_tree.py\0")
    assert dirty_tree.scope_check_main(["--plan-file", str(plan), "--paths-file", str(paths)]) == 0
    assert capsys.readouterr().out == ""


def test_scope_check_out_of_scope(tmp_path, capsys) -> None:
    plan = tmp_path / "plan.txt"
    paths = tmp_path / "paths.z"
    plan.write_text("## Files to modify\n\n### UPDATED: `python/dirty_tree.py`\n", encoding="utf-8")
    paths.write_bytes(b"README.md\0")
    assert dirty_tree.scope_check_main(["--plan-file", str(plan), "--paths-file", str(paths)]) == 1
    assert "README.md" in capsys.readouterr().err


def test_bad_baseline_path_status_unknown() -> None:
    lines = dirty_tree.baseline(baseline_path="bad path")
    assert "STATUS=unknown" in lines
    assert "REASON=bad-baseline-path" in lines


def test_checkpoint_dirty(monkeypatch) -> None:
    def fake_run_bytes(_argv: list[str]) -> tuple[int, bytes]:
        return 0, b" M python/dirty_tree.py\n"

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.checkpoint()
    assert "STATUS=dirty" in lines
    assert "REASON=checkpoint-dirty" in lines


def test_checkpoint_git_failure(monkeypatch) -> None:
    def fake_run_bytes(_argv: list[str]) -> tuple[int, bytes]:
        return 128, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.checkpoint()
    assert "STATUS=unknown" in lines
    assert "REASON=git-status-failed" in lines


def test_baseline_clean_missing_baseline_without_untracked(monkeypatch, tmp_path) -> None:
    def fake_run_bytes(argv: list[str]) -> tuple[int, bytes]:
        _ = argv
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.baseline(baseline_path=str(tmp_path / "missing.z"))
    assert "STATUS=clean" in lines
    assert "UNTRACKED_BASELINE=missing" in lines


def test_baseline_missing_with_untracked_is_ambiguous(monkeypatch, tmp_path) -> None:
    def fake_run_bytes(argv: list[str]) -> tuple[int, bytes]:
        if argv[:2] == ["git", "ls-files"]:
            return 0, b"new.txt\0"
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.baseline(baseline_path=str(tmp_path / "missing.z"))
    assert "STATUS=unknown" in lines
    assert "REASON=baseline-missing-untracked-ambiguous" in lines


def test_baseline_dirty_writes_sidecar_paths(monkeypatch, tmp_path) -> None:
    baseline = tmp_path / "baseline.z"
    baseline.write_bytes(b"old.txt\0")

    def fake_run_bytes(argv: list[str]) -> tuple[int, bytes]:
        if argv[:4] == ["git", "diff", "--name-only", "--cached"]:
            return 0, b"python/test_dirty_tree.py\0"
        if argv[:3] == ["git", "diff", "--name-only"]:
            return 0, b"python/dirty_tree.py\0"
        if argv[:2] == ["git", "ls-files"]:
            return 0, b"old.txt\0new.txt\0"
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    sidecar = tmp_path / "dirty-sidecar"
    lines = dirty_tree.baseline(baseline_path=str(baseline), sidecar=str(sidecar))
    assert "STATUS=dirty" in lines
    tracked = sidecar.with_name(sidecar.name + ".tracked-paths")
    untracked = sidecar.with_name(sidecar.name + ".new-untracked-paths")
    assert tracked.read_bytes() == b"python/dirty_tree.py\0python/test_dirty_tree.py\0"
    assert untracked.read_bytes() == b"new.txt\0"


def test_baseline_git_failure(monkeypatch, tmp_path) -> None:
    def fake_run_bytes(argv: list[str]) -> tuple[int, bytes]:
        if argv[:3] == ["git", "diff", "--name-only"]:
            return 128, b""
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.baseline(baseline_path=str(tmp_path / "baseline.z"))
    assert "STATUS=unknown" in lines
    assert "REASON=git-diff-failed" in lines


def test_baseline_main_writes_sidecar(tmp_path, monkeypatch) -> None:
    def fake_baseline(*, baseline_path: str, sidecar: str = "") -> list[str]:
        _ = baseline_path, sidecar
        return ["STATUS=clean", "MODE=baseline", "UNTRACKED_BASELINE=present"]

    monkeypatch.setattr(dirty_tree, "baseline", fake_baseline)
    sidecar = tmp_path / "baseline.out"
    assert dirty_tree.baseline_main(["--baseline", str(tmp_path / "baseline.z"), "--sidecar", str(sidecar)]) == 0
    assert sidecar.read_text(encoding="utf-8") == "STATUS=clean\nMODE=baseline\nUNTRACKED_BASELINE=present\n"


def test_checkpoint_main_disables_inherited_quiet(monkeypatch, capsys) -> None:
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    monkeypatch.setattr(dirty_tree, "checkpoint", lambda sidecar="": ["STATUS=clean", "MODE=checkpoint"])  # noqa: ARG005
    assert dirty_tree.checkpoint_main([]) == 0
    assert os.environ["LARCH_QUIET_DISABLE"] == "1"
    assert "STATUS=clean" in capsys.readouterr().out
