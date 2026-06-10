from __future__ import annotations
# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false

import os
import time
from pathlib import Path

import progress_report


def _sessions_root(home: Path) -> Path:
    root = home / ".cache" / "larch" / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_implement_pointer(home: Path, pid: str, tmpdir: Path, cwd: Path) -> Path:
    pointer = _sessions_root(home) / f"current-implement-env-{pid}.sh"
    pointer.write_text(
        f"IMPLEMENT_TMPDIR={tmpdir}\nREPO_CWD={cwd}\nSKILL_KIND=implement\n",
        encoding="utf-8",
    )
    return pointer


def _write_mark(tmpdir: Path, label: str, ts: int = 100) -> None:
    (tmpdir / "timing-ledger.tsv").write_text(
        f"v1\tmark\t{ts}\timplement\t{label}\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )


def test_no_live_run(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert progress_report._report(str(tmp_path)) == ""


def test_empty_cwd_returns_no_live_run(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    _write_mark(impl, "Step 2 — implementation")

    assert progress_report._report("") == ""


def test_design_pointer_match(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    design_tmp = tmp_path / "design"
    design_tmp.mkdir()
    (design_tmp / ".larch-keepalive").write_text(f"CLONE_PATH={cwd}\n", encoding="utf-8")
    (design_tmp / "timing-ledger.tsv").write_text(
        "v1\tmark\t100\tdesign\tStep 2 — plan review\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    env_file = tmp_path / "current-design-target.sh"
    env_file.write_text(f"export DESIGN_TMPDIR={design_tmp}\n", encoding="utf-8")
    pointer = _sessions_root(home) / "current-design-env-123.sh"
    pointer.symlink_to(env_file)

    report = progress_report._report(str(cwd))

    assert report.startswith("design: Step 2 — plan review")
    assert "last artifact:" in report


def test_implement_pointer_match_ship_pr(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    (impl / "ship-pr-state.sh").write_text(
        "PHASE=pr-create\nPR_NUMBER=42\nPR_URL=https://example.invalid/pr/42\nITERATION=2\n",
        encoding="utf-8",
    )

    report = progress_report._report(str(cwd))

    assert "Ship-PR phase: pr-create" in report
    assert "PR: #42 https://example.invalid/pr/42" in report
    assert "iteration: 2" in report


def test_implement_step5_renderer(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    _write_mark(impl, "Step 5 — code review")
    called: list[Path] = []

    def fake_step5(implement_tmpdir: Path, run_id: str) -> str:
        called.append(implement_tmpdir)
        assert run_id == ""
        return "step5 report"

    monkeypatch.setattr(progress_report, "_render_step5", fake_step5)

    assert progress_report._report(str(cwd)) == "step5 report"
    assert called == [impl]


def test_step5_done_falls_through(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    _write_mark(impl, "Step 5 — code review")
    done = impl / "progress" / "done"
    done.parent.mkdir()
    done.write_text("", encoding="utf-8")

    report = progress_report._report(str(cwd))

    assert report.startswith("implement: Step 5 — code review")


def test_stale_pointer_skipped(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    missing = tmp_path / "missing"
    _write_implement_pointer(home, "123", missing, cwd)

    assert progress_report._report(str(cwd)) == ""


def test_newest_pointer_wins(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    old_impl = tmp_path / "old"
    new_impl = tmp_path / "new"
    old_impl.mkdir()
    new_impl.mkdir()
    old_pointer = _write_implement_pointer(home, "100", old_impl, cwd)
    new_pointer = _write_implement_pointer(home, "200", new_impl, cwd)
    _write_mark(old_impl, "Step old", ts=10)
    _write_mark(new_impl, "Step new", ts=20)
    os.utime(old_pointer, (100, 100))
    os.utime(new_pointer, (200, 200))

    report = progress_report._report(str(cwd))

    assert report.startswith("implement: Step new")


def test_canonical_cwd_match(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    repo = tmp_path / "repo"
    alias = tmp_path / "alias"
    repo.mkdir()
    alias.symlink_to(repo)
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, repo)
    _write_mark(impl, "Step 2 — implementation")

    report = progress_report._report(str(alias))

    assert report.startswith("implement: Step 2 — implementation")


def test_ship_pr_stalled_phase(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    (impl / "ship-pr-state.sh").write_text(
        "PHASE=stalled\nCI_PASSED=false\nFAILED_RUN_ID=99\nSTALL_STEP=10\n",
        encoding="utf-8",
    )

    report = progress_report._report(str(cwd))

    assert "Ship-PR phase: stalled" in report
    assert "CI passed: false" in report
    assert "failed run: 99" in report
    assert "stall step: 10" in report


def test_cwd_mismatch(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    other = tmp_path / "other"
    cwd.mkdir()
    other.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)

    assert progress_report._report(str(other)) == ""


def test_dispatch_precedence(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    _write_mark(impl, "Step 5 — code review")
    (impl / "ship-pr-state.sh").write_text("PHASE=checks\n", encoding="utf-8")

    report = progress_report._report(str(cwd))

    assert report == "Ship-PR phase: checks"


def test_liveness_header_fields(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    round_dir = impl / "round-2"
    round_dir.mkdir(parents=True)
    (round_dir / "panel-manifest.ndjson").write_text("{}\n{}\n{}\n", encoding="utf-8")
    (round_dir / "collector-results.env").write_text(
        "slot1 STATUS=OK\nslot2 STATUS=FAILED\nslot3 STATUS=OK\n",
        encoding="utf-8",
    )
    start_s = int(time.time()) - 125
    (round_dir / "round-start-s").write_text(f"{start_s}\n", encoding="utf-8")
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda _tmpdir, _run_id: "detail")

    report = progress_report._render_step5(impl, "run-1")

    assert "Step 5 code review — round 2 in progress" in report
    assert "reviewers: 2/3 returned" in report
    assert "elapsed: 2m" in report
    assert report.endswith("detail")
