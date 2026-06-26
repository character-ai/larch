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


def test_scope_check_missing_inputs_returns_usage_error(tmp_path, capsys) -> None:
    paths = tmp_path / "paths.z"
    paths.write_bytes(b"python/dirty_tree.py\0")
    assert dirty_tree.scope_check_main(["--plan-file", str(tmp_path / "missing.txt"), "--paths-file", str(paths)]) == 2
    assert "plan file not found" in capsys.readouterr().err


def test_scope_marker_main_present_from_file(tmp_path) -> None:
    finding = tmp_path / "finding.md"
    finding.write_text("### FINDING_1: [SCOPE-REDUCTION] trim scope\n", encoding="utf-8")
    assert dirty_tree.scope_marker_main(["--file", str(finding)]) == 0


def test_scope_marker_main_absent_from_stdin(monkeypatch) -> None:
    class FakeStdin:
        def read(self) -> str:
            return "### FINDING_1: keep scope\n"

    monkeypatch.setattr(dirty_tree.sys, "stdin", FakeStdin())
    assert dirty_tree.scope_marker_main(["--file", "-"]) == 1


def test_scope_marker_main_missing_file_returns_one(tmp_path) -> None:
    assert dirty_tree.scope_marker_main(["--file", str(tmp_path / "missing.md")]) == 1


def test_scope_marker_main_bad_argv_returns_two() -> None:
    assert dirty_tree.scope_marker_main(["--bogus"]) == 2


def test_bad_baseline_path_status_unknown() -> None:
    lines = dirty_tree.baseline(baseline_path="bad path")
    assert "STATUS=unknown" in lines
    assert "REASON=bad-baseline-path" in lines


def test_baseline_rejects_bad_sidecar_path_without_writing(monkeypatch, tmp_path) -> None:
    calls: list[list[str]] = []

    def fake_run_bytes(argv: list[str], **_kwargs: object) -> tuple[int, bytes]:
        calls.append(argv)
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.baseline(baseline_path=str(tmp_path / "baseline.z"), sidecar=str(tmp_path / "bad sidecar"))
    assert "STATUS=unknown" in lines
    assert "REASON=bad-sidecar-path" in lines
    assert not calls
    assert not (tmp_path / "bad sidecar").exists()


def test_baseline_main_bad_sidecar_emits_reason_and_does_not_write(monkeypatch, tmp_path, capsys) -> None:
    def fake_run_bytes(**_kwargs: object) -> tuple[int, bytes]:
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    sidecar = tmp_path / "bad sidecar"
    assert dirty_tree.baseline_main(["--baseline", str(tmp_path / "baseline.z"), "--sidecar", str(sidecar)]) == 0
    out = capsys.readouterr().out
    assert "REASON=bad-sidecar-path" in out
    assert not sidecar.exists()


def test_checkpoint_dirty(monkeypatch) -> None:
    def fake_run_bytes(**_kwargs: object) -> tuple[int, bytes]:
        return 0, b" M python/dirty_tree.py\n"

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.checkpoint()
    assert "STATUS=dirty" in lines
    assert "REASON=checkpoint-dirty" in lines


def test_checkpoint_git_failure(monkeypatch) -> None:
    def fake_run_bytes(**_kwargs: object) -> tuple[int, bytes]:
        return 128, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.checkpoint()
    assert "STATUS=unknown" in lines
    assert "REASON=git-status-failed" in lines


def test_baseline_clean_missing_baseline_without_untracked(monkeypatch, tmp_path) -> None:
    def fake_run_bytes(argv: list[str], **_kwargs: object) -> tuple[int, bytes]:
        _ = argv
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.baseline(baseline_path=str(tmp_path / "missing.z"))
    assert "STATUS=clean" in lines
    assert "UNTRACKED_BASELINE=missing" in lines


def test_baseline_missing_with_untracked_is_ambiguous(monkeypatch, tmp_path) -> None:
    def fake_run_bytes(argv: list[str], **_kwargs: object) -> tuple[int, bytes]:
        if argv[:2] == ["git", "ls-files"]:
            return 0, b"new.txt\0"
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.baseline(baseline_path=str(tmp_path / "missing.z"))
    assert "STATUS=unknown" in lines
    assert "REASON=baseline-missing-untracked-ambiguous" in lines


def test_baseline_missing_with_untracked_still_writes_tracked_sidecar(monkeypatch, tmp_path) -> None:
    def fake_run_bytes(argv: list[str], **_kwargs: object) -> tuple[int, bytes]:
        if argv[:4] == ["git", "diff", "--name-only", "--cached"]:
            return 0, b"python/test_dirty_tree.py\0"
        if argv[:3] == ["git", "diff", "--name-only"]:
            return 0, b"python/dirty_tree.py\0"
        if argv[:2] == ["git", "ls-files"]:
            return 0, b"new.txt\0"
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    sidecar = tmp_path / "dirty-sidecar"
    lines = dirty_tree.baseline(baseline_path=str(tmp_path / "missing.z"), sidecar=str(sidecar))
    tracked = sidecar.with_name(sidecar.name + ".tracked-paths")
    assert "STATUS=unknown" in lines
    assert "REASON=baseline-missing-untracked-ambiguous" in lines
    assert f"TRACKED_PATHS_FILE={tracked}" in lines
    assert tracked.read_bytes() == b"python/dirty_tree.py\0python/test_dirty_tree.py\0"


def test_baseline_dirty_writes_sidecar_paths(monkeypatch, tmp_path) -> None:
    baseline = tmp_path / "baseline.z"
    baseline.write_bytes(b"old.txt\0")

    def fake_run_bytes(argv: list[str], **_kwargs: object) -> tuple[int, bytes]:
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
    def fake_run_bytes(argv: list[str], **_kwargs: object) -> tuple[int, bytes]:
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
    def fake_checkpoint(*, sidecar: str = "", cwd: str | None = None) -> list[str]:
        _ = sidecar, cwd
        return ["STATUS=clean", "MODE=checkpoint"]

    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    monkeypatch.setattr(dirty_tree, "checkpoint", fake_checkpoint)
    assert dirty_tree.checkpoint_main([]) == 0
    assert os.environ["LARCH_QUIET_DISABLE"] == "1"
    assert "STATUS=clean" in capsys.readouterr().out


def test_baseline_forwards_cwd_to_every_git_call(monkeypatch, tmp_path) -> None:
    seen_cwds: list[str | None] = []

    def fake_run_bytes(argv: list[str], cwd: str | None = None) -> tuple[int, bytes]:
        _ = argv
        seen_cwds.append(cwd)
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.baseline(baseline_path=str(tmp_path / "missing.z"), cwd="/consumer/repo")
    assert "STATUS=clean" in lines
    # status + diff + diff --cached + ls-files all run in the consumer repo, not the process CWD.
    assert seen_cwds == ["/consumer/repo", "/consumer/repo", "/consumer/repo", "/consumer/repo"]


def test_checkpoint_forwards_cwd_to_run_bytes(monkeypatch) -> None:
    seen_cwds: list[str | None] = []

    def fake_run_bytes(argv: list[str], cwd: str | None = None) -> tuple[int, bytes]:
        _ = argv
        seen_cwds.append(cwd)
        return 0, b""

    monkeypatch.setattr(dirty_tree, "_run_bytes", fake_run_bytes)  # pyright: ignore[reportPrivateUsage]
    lines = dirty_tree.checkpoint(cwd="/consumer/repo")
    assert "STATUS=clean" in lines
    assert seen_cwds == ["/consumer/repo"]


def test_run_bytes_forwards_cwd_to_subprocess(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class _Completed:
        returncode = 0
        stdout = b"out"

    def fake_run(argv: list[str], **kwargs: object) -> _Completed:
        captured["argv"] = argv
        captured["cwd"] = kwargs.get("cwd")
        return _Completed()

    monkeypatch.setattr(dirty_tree.subprocess, "run", fake_run)
    rc, out = dirty_tree._run_bytes(argv=["git", "status", "--porcelain"], cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]
    assert rc == 0
    assert out == b"out"
    assert captured["cwd"] == str(tmp_path)


def test_checkpoint_main_forwards_cwd_flag(monkeypatch, capsys) -> None:
    seen: dict[str, object] = {}

    def fake_checkpoint(*, sidecar: str = "", cwd: str | None = None) -> list[str]:
        seen["sidecar"] = sidecar
        seen["cwd"] = cwd
        return ["STATUS=clean", "MODE=checkpoint"]

    monkeypatch.setattr(dirty_tree, "checkpoint", fake_checkpoint)
    assert dirty_tree.checkpoint_main(["--cwd", "/consumer/repo"]) == 0
    assert seen["cwd"] == "/consumer/repo"
    assert "STATUS=clean" in capsys.readouterr().out


def test_checkpoint_main_cwd_falls_back_to_consumer_repo_env(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_checkpoint(*, sidecar: str = "", cwd: str | None = None) -> list[str]:
        _ = sidecar
        seen["cwd"] = cwd
        return ["STATUS=clean", "MODE=checkpoint"]

    monkeypatch.setattr(dirty_tree, "checkpoint", fake_checkpoint)
    monkeypatch.setenv("LARCH_CONSUMER_REPO", "/env/consumer/repo")
    assert dirty_tree.checkpoint_main([]) == 0
    assert seen["cwd"] == "/env/consumer/repo"


def test_checkpoint_main_cwd_flag_overrides_env(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_checkpoint(*, sidecar: str = "", cwd: str | None = None) -> list[str]:
        _ = sidecar
        seen["cwd"] = cwd
        return ["STATUS=clean", "MODE=checkpoint"]

    monkeypatch.setattr(dirty_tree, "checkpoint", fake_checkpoint)
    monkeypatch.setenv("LARCH_CONSUMER_REPO", "/env/consumer/repo")
    assert dirty_tree.checkpoint_main(["--cwd", "/flag/repo"]) == 0
    assert seen["cwd"] == "/flag/repo"


def test_checkpoint_main_cwd_unset_is_none(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_checkpoint(*, sidecar: str = "", cwd: str | None = None) -> list[str]:
        _ = sidecar
        seen["cwd"] = cwd
        return ["STATUS=clean", "MODE=checkpoint"]

    monkeypatch.setattr(dirty_tree, "checkpoint", fake_checkpoint)
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    assert dirty_tree.checkpoint_main([]) == 0
    assert seen["cwd"] is None
