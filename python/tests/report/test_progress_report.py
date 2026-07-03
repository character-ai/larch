from __future__ import annotations
# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportMissingParameterType=false, reportUnknownParameterType=false

import json
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from larch.core import config
from larch.report import progress_report


def test_round_vendor_cost_prices_claude_sub_by_model(tmp_path: Path) -> None:
    ledger = tmp_path / "larch-tokens.jsonl"
    rows = [
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "model": "claude-sonnet-4-6", "ts": "2026-06-25T00:00:05Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "model": "claude-haiku-4-5", "ts": "2026-06-25T00:00:06Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "model": "claude-fable-5", "ts": "2026-06-25T00:00:07Z"},
    ]
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert progress_report._round_vendor_cost(token_ledger=ledger, start_s=1782345600, end_s=1782345610) == "$14.00"


def test_round_vendor_cost_uses_claude_sub_raw_fallback(tmp_path: Path) -> None:
    ledger = tmp_path / "larch-tokens.jsonl"
    rows = [
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "raw": "claude_review", "ts": "2026-06-25T00:00:05Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "raw": "claude_ci_fix", "ts": "2026-06-25T00:00:06Z"},
    ]
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert progress_report._round_vendor_cost(token_ledger=ledger, start_s=1782345600, end_s=1782345610) == "$8.00"


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


def _write_design_mark(tmpdir: Path, label: str, ts: int = 100) -> None:
    (tmpdir / "timing-ledger.tsv").write_text(
        f"v1\tmark\t{ts}\tdesign\t{label}\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )


def _write_design_pointer(home: Path, pid: str, tmpdir: Path, cwd: Path) -> Path:
    tmpdir.mkdir(parents=True, exist_ok=True)
    (tmpdir / ".larch-keepalive").write_text(f"CLONE_PATH={cwd}\n", encoding="utf-8")
    env_file = tmpdir.parent / f"current-design-target-{pid}.sh"
    env_file.write_text(f"export DESIGN_TMPDIR={tmpdir}\n", encoding="utf-8")
    pointer = _sessions_root(home) / f"current-design-env-{pid}.sh"
    pointer.symlink_to(env_file)
    return pointer


def _write_plan_review_round_timing(
    ledger: Path,
    *,
    round_num: int,
    start_s: int,
    end_s: int,
) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(
            f"{start_s}\t{end_s}\tdesign\tround\tdesign Step 3 — plan review\tround-{round_num}\n"
        )


def _set_mtime(path: Path, ts: int) -> None:
    os.utime(path, (ts, ts))


def _design_run(tmpdir: Path) -> progress_report.LiveRun:
    return progress_report.LiveRun("design", tmpdir, str(tmpdir), tmpdir / "pointer", 0)


def _write_slot_manifest(manifest: Path, outputs: list[Path]) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "".join(
            f'{{"slot":"slot-{idx}","tool":"codex","output":"{output}"}}\n'
            for idx, output in enumerate(outputs, start=1)
        ),
        encoding="utf-8",
    )


def test_fallback_label_remap_annotates_executing_tool(tmp_path: Path) -> None:
    """_fallback_label_remap maps a slot's human label to a ``(via <Tool>)`` label
    when collector-results.env shows the slot was executed by a tool other than its
    nominal vendor; same-vendor slots produce no entry (issue #5838).
    """
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    arch = round_dir / "cursor-plan-arch-output.txt"
    pragmatic = round_dir / "codex-plan-pragmatic-output.txt"
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "cursor-plan-arch", "tool": "cursor", "output": str(arch)}) + "\n"
        + json.dumps({"slot": "codex-plan-pragmatic", "tool": "codex", "output": str(pragmatic)}) + "\n",
        encoding="utf-8",
    )
    (design / "collector-results.env").write_text(
        f"REVIEWER_FILE={arch}\nTOOL=codex\nSTATUS=OK\n\n"
        f"REVIEWER_FILE={pragmatic}\nTOOL=codex\nSTATUS=OK\n\n",
        encoding="utf-8",
    )

    remap = progress_report._fallback_label_remap([round_dir])

    assert remap == {"Cursor-Arch": "Cursor-Arch (via Codex)"}


def test_fallback_label_remap_annotates_code_review_parent_collector(tmp_path: Path) -> None:
    root = tmp_path / "review"
    round_dir = root / "round-1"
    round_dir.mkdir(parents=True)
    output = "cursor-specialist-arch-output.txt"
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "arch", "tool": "cursor", "output": output}) + "\n",
        encoding="utf-8",
    )
    (root / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\nTOOL=codex\nSTATUS=OK\n\n",
        encoding="utf-8",
    )

    remap = progress_report._fallback_label_remap([round_dir])

    assert not (round_dir / "collector-results.env").exists()
    assert remap == {"cursor/arch": "cursor/arch (via Codex)"}


def test_fallback_label_remap_prefers_round_local_collector(tmp_path: Path) -> None:
    root = tmp_path / "review"
    round_dir = root / "round-1"
    round_dir.mkdir(parents=True)
    output = "cursor-specialist-arch-output.txt"
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "arch", "tool": "cursor", "output": output}) + "\n",
        encoding="utf-8",
    )
    (round_dir / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\nTOOL=codex\nSTATUS=OK\n\n",
        encoding="utf-8",
    )
    (root / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\nTOOL=cursor\nSTATUS=OK\n\n",
        encoding="utf-8",
    )

    remap = progress_report._fallback_label_remap([round_dir])

    assert remap == {"cursor/arch": "cursor/arch (via Codex)"}


def test_fallback_label_remap_empty_without_collector(tmp_path: Path) -> None:
    """No collector-results.env -> no remap (issue #5838)."""
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "cursor-plan-arch", "tool": "cursor", "output": str(round_dir / "cursor-plan-arch-output.txt")}) + "\n",
        encoding="utf-8",
    )
    assert not progress_report._fallback_label_remap([round_dir])


def _write_output(path: Path, ts: int, text: str = "done\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _set_mtime(path, ts)
    return path


def _write_vendor_timing(
    ledger: Path,
    output: str,
    start_s: int,
    end_s: int,
    *,
    vendor: str = "codex",
    kind: str = "codex-review",
    status: str = "complete",
    skill: str = "implement",
) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0, end_s - start_s)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(
            f"v1\tvendor\t{end_s}\t{skill}\t-\t{vendor}\t{kind}\t{start_s}\t{end_s}\t"
            f"{duration}\t{output}\t0\t{status}\n"
        )


def _write_round_timing(
    ledger: Path,
    *,
    skill: str,
    round_num: int,
    start_s: int,
    end_s: int,
    attempt: int | None = None,
) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0, end_s - start_s)
    # Issue #5504: trailing column holds the 1-based attempt index; None reproduces legacy
    # rows (written "-") to keep backward-compat coverage honest.
    attempt_col = "-" if attempt is None else str(attempt)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(
            f"v1\tround\t{start_s}\t{skill}\t-\t{round_num}\t{start_s}\t{end_s}\t"
            f"{duration}\t0\t0\t0\t{attempt_col}\n"
        )


_MINIMAL_ROUND_META = (
    '{"tally":{"ACCEPTED_COUNT":"0","REJECTED_COUNT":"0","EXONERATED_COUNT":"0",'
    '"NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},'
    '"summary":{"panel":{"total_slot_count":1}}}'
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


def test_report_cli_stdout_not_rerouted_by_quiet_env(tmp_path: Path) -> None:
    home = tmp_path / "home"
    cwd = tmp_path / "repo"
    cwd.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    _write_mark(impl, "Step 2 — implementation")
    quiet_log = tmp_path / "quiet.log"
    report_text = "implement: Step 2 — implementation"
    env = os.environ.copy()
    env["HOME"] = str(home)
    env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    env[config.ENV_LARCH_QUIET_ACTIVE] = "1"
    env[config.ENV_LARCH_QUIET_PID] = "999999"
    env[config.ENV_LARCH_QUIET_LOG_FILE] = str(quiet_log)

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[2] / "cli.py"),
            "progress",
            "report",
            "--cwd",
            str(cwd),
        ],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert report_text in result.stdout
    quiet_text = quiet_log.read_text(encoding="utf-8") if quiet_log.exists() else ""
    assert report_text not in quiet_text


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


def test_latest_timing_ledger_activity_ts_recognizes_plan_review_round_row(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_plan_review_round_timing(ledger, round_num=1, start_s=100, end_s=200)

    assert progress_report._latest_timing_ledger_activity_ts(ledger) == 200


def test_active_design_step3_wins_when_stale_run_has_newer_pointer(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    active_design = tmp_path / "active-design"
    stale_design = tmp_path / "stale-design"
    active_pointer = _write_design_pointer(home, "100", active_design, cwd)
    stale_pointer = _write_design_pointer(home, "200", stale_design, cwd)
    _write_design_mark(active_design, "Step 3 — plan review", ts=10)
    _write_plan_review_round_timing(
        active_design / "timing-ledger.tsv",
        round_num=1,
        start_s=300,
        end_s=600,
    )
    os.utime(active_pointer, (100, 100))
    os.utime(stale_pointer, (500, 500))

    report = progress_report._report(str(cwd))

    assert report.startswith("design: Step 3 — plan review")
    assert "unknown step" not in report


def test_design_ranking_falls_back_to_pointer_mtime_without_ledger_activity(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    old_design = tmp_path / "old-design"
    new_design = tmp_path / "new-design"
    old_pointer = _write_design_pointer(home, "100", old_design, cwd)
    new_pointer = _write_design_pointer(home, "200", new_design, cwd)
    (old_design / "timing-ledger.tsv").write_text("not-a-valid-row\n", encoding="utf-8")
    (new_design / "timing-ledger.tsv").write_text("also-not-a-valid-row\n", encoding="utf-8")
    (old_design / "old-artifact.txt").write_text("old\n", encoding="utf-8")
    (new_design / "new-artifact.txt").write_text("new\n", encoding="utf-8")
    os.utime(old_pointer, (100, 100))
    os.utime(new_pointer, (200, 200))

    report = progress_report._report(str(cwd))

    assert report.startswith("design: unknown step")
    assert "new-artifact.txt" in report
    assert "old-artifact.txt" not in report


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


def test_implement_pointer_match_ship_pr_unlisted_phase(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    _write_mark(impl, "Step 0 — preflight")
    (impl / "ship-pr-state.sh").write_text("PHASE=bump\n", encoding="utf-8")

    report = progress_report._report(str(cwd))

    assert report == "Ship-PR phase: bump"


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

    def fake_step5(*, implement_tmpdir: Path, run_id: str, window_start_s: int | None = None) -> str:
        called.append(implement_tmpdir)
        assert run_id == ""
        assert window_start_s == 100
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


def test_newest_implement_pointer_wins(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
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
    # Tmpdir mtimes run opposite to pointer mtimes: the newest pointer must win
    # even when its tmpdir root has older direct activity.
    os.utime(old_pointer, (100, 100))
    os.utime(new_pointer, (200, 200))
    _set_mtime(old_impl, 200)
    _set_mtime(new_impl, 100)

    report = progress_report._report(str(cwd))

    assert report.startswith("implement: Step new")


def test_newer_pointer_active_tmpdir_wins_over_stale_tmpdir_activity(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    stale_impl = tmp_path / "stale"
    active_impl = tmp_path / "active"
    stale_impl.mkdir()
    active_impl.mkdir()
    stale_pointer = _write_implement_pointer(home, "100", stale_impl, cwd)
    active_pointer = _write_implement_pointer(home, "200", active_impl, cwd)
    _write_mark(stale_impl, "Step 0 — preflight", ts=10)
    _write_mark(active_impl, "Step 5 — code review", ts=20)
    round_dir = active_impl / "round-1"
    round_dir.mkdir()
    (round_dir / "panel-manifest.ndjson").write_text("{}\n{}\n{}\n", encoding="utf-8")
    # Reproduce the reported mtime race: the stale tmpdir root has newer direct
    # activity, while the active session has the newer pointer file.
    os.utime(stale_pointer, (100, 100))
    os.utime(active_pointer, (300, 300))
    _set_mtime(stale_impl, 300)
    _set_mtime(active_impl, 100)

    report = progress_report._report(str(cwd))

    assert "Step 5 code review" in report
    assert "Step 0" not in report


def test_step5_active_pointer_wins_when_failed_tmpdir_root_newer(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    failed_impl = tmp_path / "failed"
    active_impl = tmp_path / "active"
    failed_impl.mkdir()
    active_impl.mkdir()
    failed_pointer = _write_implement_pointer(home, "100", failed_impl, cwd)
    active_pointer = _write_implement_pointer(home, "200", active_impl, cwd)
    _write_mark(failed_impl, "Step 0 — preflight", ts=10)
    _write_mark(active_impl, "Step 5 — code review", ts=20)
    (failed_impl / "copy-plan.stderr.log").write_text("copy failed\n", encoding="utf-8")
    os.utime(failed_pointer, (100, 100))
    os.utime(active_pointer, (200, 200))
    _set_mtime(failed_impl, 300)
    _set_mtime(active_impl, 100)
    rendered: list[Path] = []

    def fake_step5(*, implement_tmpdir: Path, run_id: str, window_start_s: int | None = None) -> str:
        rendered.append(implement_tmpdir)
        assert run_id == ""
        assert window_start_s == 20
        return "active step5 report"

    monkeypatch.setattr(progress_report, "_render_step5", fake_step5)

    report = progress_report._report(str(cwd))

    assert report == "active step5 report"
    assert rendered == [active_impl]


def test_active_step5_wins_when_stale_run_has_newer_pointer(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """#4954: live Step 5 session ranks above a stale Step 0 run with a newer pointer.

    The implement pointer is written once at Step 0 and never refreshed, so a long-running
    review session has a frozen pointer mtime. A later run that stalls at Step 0 owns a newer
    pointer and can also own a fresher Step 0 mark timestamp. Ranking by mark alone would pick
    the stale run even while Step 5 vendor ledger rows keep advancing on the live session.
    """
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cwd = tmp_path / "repo"
    cwd.mkdir()
    stale_impl = tmp_path / "stale"
    active_impl = tmp_path / "active"
    stale_impl.mkdir()
    active_impl.mkdir()
    stale_pointer = _write_implement_pointer(home, "100", stale_impl, cwd)
    active_pointer = _write_implement_pointer(home, "200", active_impl, cwd)
    _write_mark(stale_impl, "Step 0 — preflight", ts=20)
    _write_mark(active_impl, "Step 5 — code review", ts=10)
    round_dir = active_impl / "round-1"
    round_dir.mkdir()
    (round_dir / "panel-manifest.ndjson").write_text("{}\n{}\n{}\n", encoding="utf-8")
    _write_vendor_timing(
        active_impl / "timing-ledger.tsv",
        "cursor-specialist-correctness-output.txt",
        15,
        25,
    )
    # Live session: older pointer (frozen at Step 0), older Step 5 mark (ts=10), and older
    # tmpdir-root mtime; ongoing review vendor rows (end ts=25) keep it live. Stale run:
    # newer pointer and fresher Step 0 mark (ts=20) but no Step 5 activity.
    os.utime(active_pointer, (100, 100))
    os.utime(stale_pointer, (300, 300))
    _set_mtime(active_impl, 100)
    _set_mtime(stale_impl, 300)

    report = progress_report._report(str(cwd))

    assert "Step 5 code review" in report
    assert "Step 0" not in report


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
    round_dir = impl / "round-1"
    round_dir.mkdir()
    _write_implement_pointer(home, "123", impl, cwd)
    _write_mark(impl, "Step 5 — code review")
    (round_dir / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    (impl / "ship-pr-state.sh").write_text("PHASE=checks\n", encoding="utf-8")

    report = progress_report._report(str(cwd))

    assert "Step 5 code review — round 1 in progress" in report
    assert "Ship-PR phase: checks" not in report


def test_liveness_header_fields(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    round_dir = impl / "round-2"
    round_dir.mkdir(parents=True)
    (round_dir / "panel-manifest.ndjson").write_text("{}\n{}\n{}\n", encoding="utf-8")
    (round_dir / "collector-results.env").write_text(
        "slot1 STATUS=OK\nslot2 STATUS=FAILED\nslot3 STATUS=OK\n",
        encoding="utf-8",
    )
    (round_dir / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    start_s = int(time.time()) - 125
    (round_dir / "round-start-s").write_text(f"{start_s}\n", encoding="utf-8")
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda **_k: "detail")

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1")

    assert "Step 5 code review — round 2 in progress" in report
    assert "reviewers: 2/3 returned" in report
    assert "elapsed: 2m" in report
    assert report.endswith("detail")


def test_step5_between_rounds_keeps_latest_round_liveness(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "review-and-fix.env").write_text("STATUS=complete\n", encoding="utf-8")
    (round_dir / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    (round_dir / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda **_k: "detail")

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1")

    assert "round 1 in progress" in report
    assert report.endswith("detail")


def test_review_rounds_root_prefers_flushed_log_during_live_round(tmp_path: Path) -> None:
    impl = tmp_path / "impl"
    run_id = "run-1"
    flushed = impl / "larch-logs" / "implement" / run_id / "round-1"
    live = impl / "round-2"
    flushed.mkdir(parents=True)
    live.mkdir(parents=True)
    (flushed / "review-and-fix.env").write_text("", encoding="utf-8")
    (live / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    (live / "round-start-s").write_text("100\n", encoding="utf-8")

    assert progress_report._review_rounds_root(implement_tmpdir=impl, run_id=run_id) == flushed.parent
    report = progress_report._render_step5(implement_tmpdir=impl, run_id=run_id)
    assert "round 2 in progress" in report


def test_render_review_detail_argv(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    run_id = "run-1"
    flushed = impl / "larch-logs" / "implement" / run_id / "round-1"
    flushed.mkdir(parents=True)
    (flushed / "review-and-fix.env").write_text("", encoding="utf-8")
    (impl / "timing-ledger.tsv").write_text("v1\tmark\t1\timplement\tStep 5\t-\t-\t-\t-\t-\t-\t-\t-\n", encoding="utf-8")
    captured: list[dict[str, object]] = []

    def fake_render(*args: object, **kwargs: object) -> str:
        kwargs["rounds_root"] = args[0]
        captured.append(kwargs)
        return "detail-table"

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)

    detail = progress_report._render_review_detail(implement_tmpdir=impl, run_id=run_id)

    assert detail == "detail-table"
    assert captured
    kwargs = captured[0]
    assert kwargs["rounds_root"] == flushed.parent
    assert kwargs["timing_ledger"] == impl / "timing-ledger.tsv"
    assert kwargs["skill"] == "implement"


def test_strip_md_for_terminal() -> None:
    raw = (
        "## Review Phase Detail\n\n"
        "| Round | Suggestions |\n"
        "|--:|--:|\n"
        "| 1 | 17 |\n"
        "| **Total** | **17** |\n\n"
        "**Top reviewers** (by suggestions accepted):\n"
        "- slot/arch — 3\n\n"
        "_Cost is a footnote._\n"
    )
    stripped = progress_report._strip_md_for_terminal(raw)
    assert "## " not in stripped
    assert "|--:" not in stripped
    assert "**" not in stripped
    assert "_Cost" not in stripped
    assert "Review Phase Detail" in stripped
    assert "| 1 | 17 |" in stripped
    assert "| Total | 17 |" in stripped
    assert "Top reviewers" in stripped
    assert "Cost is a footnote." in stripped


def test_render_review_detail_strips_markdown(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    run_id = "run-1"
    flushed = impl / "larch-logs" / "implement" / run_id / "round-1"
    flushed.mkdir(parents=True)
    (flushed / "review-and-fix.env").write_text("", encoding="utf-8")
    (impl / "timing-ledger.tsv").write_text("v1\tmark\t1\timplement\tStep 5\t-\t-\t-\t-\t-\t-\t-\t-\n", encoding="utf-8")

    md_output = "## Review Phase Detail\n\n| Round |\n|--:|\n| **1** |\n\n_Footnote._\n"

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return md_output

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)

    detail = progress_report._render_review_detail(implement_tmpdir=impl, run_id=run_id)

    assert "## " not in detail
    assert "|--:" not in detail
    assert "**" not in detail
    assert "Review Phase Detail" in detail
    assert "| 1 |" in detail
    assert "Footnote." in detail


def test_all_round_dirs_inflight_no_round_dirs(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    assert progress_report._all_round_dirs_inflight(root) is False


def test_all_round_dirs_inflight_all_missing_meta(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "round-1").mkdir(parents=True)
    assert progress_report._all_round_dirs_inflight(root) is True


def test_all_round_dirs_inflight_one_completed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "round-1").mkdir(parents=True)
    (root / "round-2").mkdir(parents=True)
    (root / "round-1" / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    assert progress_report._all_round_dirs_inflight(root) is False


def test_progress_label_fallbacks_and_manifest_precedence(tmp_path: Path) -> None:
    assert progress_report._derive_progress_label(output="aggregator-output.txt") == "aggregator"
    assert progress_report._derive_progress_label(output="scout-plan-manifest.json.raw") == "scout"
    assert (
        progress_report._derive_progress_label(
            output="codex-output.txt",
            vendor="codex",
            kind="codex-plan-autofix",
        )
        == "codex/apply"
    )
    assert (
        progress_report._derive_progress_label(
            output="cursor-output.txt",
            vendor="cursor",
            kind="cursor-plan-autofix",
        )
        == "cursor/apply"
    )
    assert progress_report._derive_progress_label(output="coder-codex.log", vendor="codex", kind="codex-review-fix") == "codex/apply"
    assert progress_report._derive_progress_label(output="coder-cursor.log", vendor="cursor", kind="cursor-review-fix") == "cursor/apply"

    output = tmp_path / "codex-output.txt"
    manifest = tmp_path / "panel-manifest.ndjson"
    manifest.write_text(f'{{"slot":"mapped","tool":"tool","output":"{output}"}}\n', encoding="utf-8")
    label_map = progress_report._progress_label_map_from_manifests([manifest])
    assert progress_report._derive_progress_label(output=str(output), vendor="codex", kind="codex-plan-autofix", label_map=label_map) == "codex/apply"


def test_progress_vendor_rows_use_apply_task_kind_priority(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_vendor_timing(
        ledger,
        "codex-output.txt",
        110,
        140,
        vendor="codex",
        kind="codex-plan-autofix",
    )
    _write_vendor_timing(
        ledger,
        "coder-cursor.log",
        141,
        170,
        vendor="cursor",
        kind="cursor-review-fix",
    )
    _write_vendor_timing(
        ledger,
        "coder-codex.log",
        171,
        190,
        vendor="codex",
        kind="codex-review-fix",
    )

    rows = progress_report._progress_vendor_rows(timing_ledger=ledger, window_start_s=100, window_end_s=200, label_map={})

    assert [row.label for row in rows] == ["codex/apply", "cursor/apply", "codex/apply"]


def test_progress_vendor_rows_skip_ci_rows_when_requested(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_vendor_timing(ledger, "codex-specialist-correctness-output.txt", 110, 140)
    _write_vendor_timing(ledger, "reviewer-output.txt", 111, 141, kind="codex-ci")
    _write_vendor_timing(ledger, "reviewer-output.txt", 112, 142, kind="cursor-ci-fix")
    _write_vendor_timing(ledger, "reviewer-output.txt", 113, 143, kind="vendor-ci-test")
    _write_vendor_timing(ledger, "ci.out", 114, 144)
    _write_vendor_timing(ledger, "codex-ci.out", 115, 145)
    _write_vendor_timing(ledger, "ci-fix-codex.out", 116, 146)
    _write_vendor_timing(ledger, "claude.out", 117, 147)
    _write_vendor_timing(ledger, str(tmp_path / "nested" / "cursor-ci.out"), 118, 148)

    rows = progress_report._progress_vendor_rows(timing_ledger=ledger, window_start_s=100, window_end_s=200, label_map={}, skip_ci=True)

    assert len(rows) == 1
    assert rows[0].label == "codex/correctness"


def test_progress_vendor_rows_reserve_coder_apply_under_cap(tmp_path: Path) -> None:
    # Issue #5264: the coder fix-application lane (cursor/codex applying review
    # suggestions) starts after every reviewer, aggregator, and voter row, so a
    # full panel that fills PROGRESS_GANTT_ROW_CAP pushes the late-starting
    # apply row past the start-sorted cap and the chart silently omits it.
    ledger = tmp_path / "timing-ledger.tsv"
    for i in range(progress_report.PROGRESS_GANTT_ROW_CAP):
        _write_vendor_timing(
            ledger,
            "codex-specialist-correctness-output.txt",
            100 + i,
            150,
            vendor="codex",
            kind="codex-review",
        )
    _write_vendor_timing(
        ledger,
        "coder-cursor.log",
        200,
        300,
        vendor="cursor",
        kind="cursor-review-fix",
    )

    rows = progress_report._progress_vendor_rows(timing_ledger=ledger, window_start_s=100, window_end_s=400, label_map={})

    labels = [row.label for row in rows]
    assert len(rows) == progress_report.PROGRESS_GANTT_ROW_CAP
    # The apply lane is reserved; the latest-starting reviewer row is dropped instead.
    assert labels.count("cursor/apply") == 1
    assert labels.count("codex/correctness") == progress_report.PROGRESS_GANTT_ROW_CAP - 1


def test_progress_vendor_rows_cap_without_apply_keeps_earliest(tmp_path: Path) -> None:
    # Backward compatibility: with no coder-apply lane present, the row cap still
    # keeps the earliest-starting rows and drops the latest, exactly as the
    # pre-#5264 start-sorted truncation did.
    ledger = tmp_path / "timing-ledger.tsv"
    over_cap = progress_report.PROGRESS_GANTT_ROW_CAP + 2
    for i in range(over_cap):
        _write_vendor_timing(
            ledger,
            "codex-specialist-correctness-output.txt",
            100 + i,
            150,
            vendor="codex",
            kind="codex-review",
        )

    rows = progress_report._progress_vendor_rows(timing_ledger=ledger, window_start_s=100, window_end_s=400, label_map={})

    assert len(rows) == progress_report.PROGRESS_GANTT_ROW_CAP
    starts = [row.start_s for row in rows]
    # The two latest-starting rows are dropped; the earliest cap rows survive.
    assert max(starts) == 100 + progress_report.PROGRESS_GANTT_ROW_CAP - 1


def test_render_step5_inflight_only_skips_detail(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")

    def fail_detail(_tmpdir: Path, _run_id: str) -> str:
        raise AssertionError("_render_review_detail must not run for inflight-only root")

    monkeypatch.setattr(progress_report, "_render_review_detail", fail_detail)

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1")

    assert "Step 5 code review — round 1 in progress" in report
    assert "No review rounds completed." not in report


def test_render_step5_first_round_inflight_gantt(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 200)
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    output = round_dir / "codex-output.txt"
    round_dir.mkdir(parents=True)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    (round_dir / "panel-manifest.ndjson").write_text(
        f'{{"slot":"slot","tool":"tool","output":"{output}"}}\n',
        encoding="utf-8",
    )
    _write_vendor_timing(impl / "timing-ledger.tsv", str(output), 120, 170)
    _write_vendor_timing(
        impl / "timing-ledger.tsv",
        "coder-cursor.log",
        171,
        180,
        vendor="cursor",
        kind="cursor-review-fix",
    )
    _write_vendor_timing(
        impl / "timing-ledger.tsv",
        "codex-output.txt",
        181,
        190,
        vendor="codex",
        kind="codex-plan-autofix",
    )

    def fail_detail(_tmpdir: Path, _run_id: str) -> str:
        raise AssertionError("_render_review_detail must not run without completed metadata")

    monkeypatch.setattr(progress_report, "_render_review_detail", fail_detail)

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1")

    assert "Step 5 code review — round 1 in progress" in report
    assert "Round 1 reviewer timing" in report
    assert "tool/slot" in report
    assert "cursor/apply" in report
    assert "codex/apply" in report


def test_render_step5_inflight_gantt_uses_step_mark_start_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 200)
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    output = round_dir / "codex-output.txt"
    round_dir.mkdir(parents=True)
    _set_mtime(round_dir, 150)
    (round_dir / "panel-manifest.ndjson").write_text(
        f'{{"slot":"slot","tool":"tool","output":"{output}"}}\n',
        encoding="utf-8",
    )
    _write_vendor_timing(impl / "timing-ledger.tsv", str(output), 120, 140)

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1", window_start_s=100)

    assert "Round 1 reviewer timing" in report
    assert "tool/slot" in report


def test_render_step5_mixed_state_still_renders_detail(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    completed = impl / "round-1"
    inflight = impl / "round-2"
    completed.mkdir(parents=True)
    inflight.mkdir(parents=True)
    (completed / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    (inflight / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    (inflight / "round-start-s").write_text("100\n", encoding="utf-8")
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda **_k: "sentinel-detail")

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1")

    assert "sentinel-detail" in report


def test_render_step5_mixed_state_appends_inflight_gantt(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    impl = tmp_path / "impl"
    completed = impl / "round-1"
    inflight = impl / "round-2"
    output = inflight / "cursor-output.txt"
    completed.mkdir(parents=True)
    inflight.mkdir(parents=True)
    (completed / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    (inflight / "round-start-s").write_text("100\n", encoding="utf-8")
    (inflight / "panel-manifest.ndjson").write_text(
        f'{{"slot":"slot","tool":"cursor","output":"{output}"}}\n',
        encoding="utf-8",
    )
    _write_vendor_timing(
        impl / "timing-ledger.tsv",
        str(output),
        130,
        180,
        vendor="cursor",
        kind="cursor-review",
    )
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda **_k: "completed-detail")

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1")

    assert "completed-detail" in report
    assert "Round 2 reviewer timing" in report
    assert "cursor/slot" in report


def test_render_step5_round_two_without_start_uses_prior_round_end_only(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    impl = tmp_path / "impl"
    completed = impl / "round-1"
    inflight = impl / "round-2"
    current_output = inflight / "cursor-specialist-current-output.txt"
    completed.mkdir(parents=True)
    inflight.mkdir(parents=True)
    (completed / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    (inflight / "panel-manifest.ndjson").write_text(
        f'{{"slot":"current","tool":"cursor","output":"{current_output}"}}\n',
        encoding="utf-8",
    )
    _write_round_timing(impl / "timing-ledger.tsv", skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(impl / "timing-ledger.tsv", "cursor-specialist-round-one-output.txt", 120, 180)
    _write_vendor_timing(impl / "timing-ledger.tsv", "aggregator-output.txt", 181, 190, vendor="claude", kind="vendor-misc")
    _write_vendor_timing(impl / "timing-ledger.tsv", "claude-vote-output.txt", 191, 199, vendor="claude", kind="vote")
    _write_vendor_timing(impl / "timing-ledger.tsv", str(current_output), 210, 260, vendor="cursor", kind="cursor-review")
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda **_k: "completed-detail")

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1", window_start_s=90)

    assert "Round 2 reviewer timing" in report
    assert "cursor/current" in report
    assert "cursor/round-one" not in report
    assert "aggregator" not in report
    assert "claude/vote" not in report


def test_render_design_plan_review_inflight_only_skips_detail(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 120)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)

    def fail_detail(_tmpdir: Path) -> str:
        raise AssertionError("_render_design_review_detail must not run for inflight-only root")

    monkeypatch.setattr(progress_report, "_render_design_review_detail", fail_detail)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "Step 3 plan review — round 1 in progress" in report
    assert "No review rounds completed." not in report


def test_render_design_plan_review_inflight_gantt_uses_root_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    output = design / "codex-output.txt"
    round_dir.mkdir(parents=True)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_output(output, 130)
    _write_slot_manifest(design / "plan-review-slots.ndjson", [output])
    _set_mtime(design / "plan-review-slots.ndjson", 120)
    _write_vendor_timing(design / "timing-ledger.tsv", str(output), 125, 180)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "Step 3 plan review — round 1 in progress" in report
    assert "Round 1 reviewer timing" in report
    assert "codex/slot-1" in report


def test_render_design_plan_review_mixed_state_still_renders_detail(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    design = tmp_path / "design"
    completed = design / "plan-review" / "round-1"
    inflight = design / "plan-review" / "round-2"
    completed.mkdir(parents=True)
    inflight.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 120)
    (completed / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    (inflight / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(inflight / "panel-manifest.ndjson", [out])
    _set_mtime(inflight / "panel-manifest.ndjson", 120)
    monkeypatch.setattr(
        progress_report,
        "_render_design_review_detail",
        lambda _tmpdir: "sentinel-design-detail",
    )

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "sentinel-design-detail" in report


def test_render_design_plan_review_mixed_state_appends_inflight_gantt(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    design = tmp_path / "design"
    completed = design / "plan-review" / "round-1"
    inflight = design / "plan-review" / "round-2"
    output = design / "cursor-output.txt"
    completed.mkdir(parents=True)
    inflight.mkdir(parents=True)
    (completed / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    (inflight / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_output(output, 130)
    _write_slot_manifest(inflight / "panel-manifest.ndjson", [output])
    _set_mtime(inflight / "panel-manifest.ndjson", 120)
    _write_vendor_timing(
        design / "timing-ledger.tsv",
        str(output),
        125,
        180,
        vendor="cursor",
        kind="cursor-review",
    )
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "completed-design-detail")

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "completed-design-detail" in report
    assert "Round 2 reviewer timing" in report
    assert "codex/slot-1" in report


def test_render_design_round_two_without_start_uses_prior_round_end_only(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    design = tmp_path / "design"
    completed = design / "plan-review" / "round-1"
    inflight = design / "plan-review" / "round-2"
    current_output = design / "cursor-current-output.txt"
    completed.mkdir(parents=True)
    inflight.mkdir(parents=True)
    (completed / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    _write_output(current_output, 210)
    _write_slot_manifest(inflight / "panel-manifest.ndjson", [current_output])
    _set_mtime(inflight / "panel-manifest.ndjson", 205)
    _write_round_timing(design / "timing-ledger.tsv", skill="design", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(
        design / "timing-ledger.tsv",
        "cursor-specialist-round-one-output.txt",
        120,
        180,
        skill="design",
    )
    _write_vendor_timing(
        design / "timing-ledger.tsv",
        "aggregator-output.txt",
        181,
        190,
        vendor="claude",
        kind="vendor-misc",
        skill="design",
    )
    _write_vendor_timing(
        design / "timing-ledger.tsv",
        "claude-vote-output.txt",
        191,
        199,
        vendor="claude",
        kind="vote",
        skill="design",
    )
    _write_vendor_timing(
        design / "timing-ledger.tsv",
        str(current_output),
        210,
        260,
        vendor="cursor",
        kind="cursor-review",
        skill="design",
    )
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "completed-design-detail")

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "Round 2 reviewer timing" in report
    assert "codex/slot-1" in report
    assert "cursor/round-one" not in report
    assert "aggregator" not in report
    assert "claude/vote" not in report


def test_render_inflight_gantt_ignores_round_n_minus_two_when_prior_round_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 500)
    impl = tmp_path / "impl"
    round_one = impl / "round-1"
    round_two = impl / "round-2"
    round_three = impl / "round-3"
    current_output = round_three / "cursor-specialist-current-output.txt"
    round_one.mkdir(parents=True)
    round_two.mkdir(parents=True)
    round_three.mkdir(parents=True)
    (round_one / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    (round_two / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    (round_three / "panel-manifest.ndjson").write_text(
        f'{{"slot":"current","tool":"cursor","output":"{current_output}"}}\n',
        encoding="utf-8",
    )
    _set_mtime(round_three, 400)
    _write_round_timing(impl / "timing-ledger.tsv", skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(impl / "timing-ledger.tsv", "cursor-specialist-orphan-round-two-output.txt", 250, 260)
    _write_vendor_timing(impl / "timing-ledger.tsv", str(current_output), 410, 450, vendor="cursor", kind="cursor-review")
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda **_k: "completed-detail")

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1", window_start_s=90)

    assert "Round 3 reviewer timing" in report
    assert "cursor/current" in report
    assert "cursor/orphan-round-two" not in report


def test_render_inflight_gantt_absent_without_completed_vendor_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 200)
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    (round_dir / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    _write_vendor_timing(impl / "timing-ledger.tsv", "codex-output.txt", 120, 150, status="signal")

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1")

    assert "Step 5 code review — round 1 in progress" in report
    assert "Round 1 reviewer timing" not in report


def test_render_step5_inflight_gantt_absent_with_only_ci_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 200)
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    (round_dir / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    _write_vendor_timing(impl / "timing-ledger.tsv", "codex-output.txt", 120, 150, kind="codex-ci")
    _write_vendor_timing(impl / "timing-ledger.tsv", "ci-fix-codex.out", 130, 160)

    report = progress_report._render_step5(implement_tmpdir=impl, run_id="run-1")

    assert "Step 5 code review — round 1 in progress" in report
    assert "Round 1 reviewer timing" not in report


def test_design_step3_no_round_dirs_falls_through_to_generic(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _write_design_mark(design, "Step 3 — plan review", ts=100)

    report = progress_report._render_design(_design_run(design))

    assert report.startswith("design: Step 3 — plan review")
    assert "last artifact:" in report


def test_design_step3_header_only_with_fresh_round_local_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    fresh = _write_output(design / "slot-1-output.txt", 110)
    stale = _write_output(design / "slot-2-output.txt", 90)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [fresh, stale])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "Step 3 plan review — round 1 in progress" in report
    assert "reviewers: 1/2 returned | elapsed: 2m" in report


def test_design_step3_appends_stripped_detail(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 120)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    (round_dir / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return "## Review Phase Detail\n\n| Round |\n|--:|\n| **1** |\n"

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "Review Phase Detail" in report
    assert "## " not in report
    assert "|--:" not in report
    assert "**" not in report


def test_design_step3_label_triggers_rich_view(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    design = tmp_path / "design"
    design.mkdir()
    _write_design_mark(design, "Step 3 — plan review", ts=100)

    monkeypatch.setattr(progress_report, "_render_design_plan_review", lambda **_k: "rich")

    assert progress_report._render_design(_design_run(design)) == "rich"


def test_design_non_step3_label_skips_rich_view(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    design = tmp_path / "design"
    design.mkdir()
    _write_design_mark(design, "Step 2 — planning", ts=100)

    def fail_rich(**_kw: object) -> str:
        raise AssertionError("rich renderer should not run")

    monkeypatch.setattr(progress_report, "_render_design_plan_review", fail_rich)

    report = progress_report._render_design(_design_run(design))

    assert report.startswith("design: Step 2 — planning")


def test_design_step3_no_usable_rounds_falls_through_to_generic(tmp_path: Path) -> None:
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _write_design_mark(design, "Step 3 — plan review", ts=200)
    stale = _write_output(design / "slot-output.txt", 90)
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [stale])
    _set_mtime(round_dir / "panel-manifest.ndjson", 100)

    report = progress_report._render_design(_design_run(design))

    assert report.startswith("design: Step 3 — plan review")
    assert "Step 3 plan review — round 1 in progress" not in report


def test_design_detail_argv_uses_design_skill_and_rounds_root(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    design = tmp_path / "design"
    (design / "plan-review").mkdir(parents=True)
    (design / "timing-ledger.tsv").write_text("ledger\n", encoding="utf-8")
    captured: list[dict[str, object]] = []

    def fake_render(*args: object, **kwargs: object) -> str:
        kwargs["rounds_root"] = args[0]
        captured.append(kwargs)
        return "detail"

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)

    detail = progress_report._render_design_review_detail(design)

    assert detail == "detail"
    kwargs = captured[0]
    assert kwargs["skill"] == "design"
    assert kwargs["rounds_root"] == design / "plan-review"
    assert kwargs["timing_ledger"] == design / "timing-ledger.tsv"


def test_design_live_root_manifest_counts_after_child_write(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    outputs = [
        _write_output(design / "slot-1-output.txt", 130),
        _write_output(design / "slot-2-output.txt", 130),
        design / "slot-3-output.txt",
    ]
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(design / "plan-review-slots.ndjson", outputs)
    _set_mtime(design / "plan-review-slots.ndjson", 120)
    (round_dir / "dispatch-child.log").write_text("later\n", encoding="utf-8")
    _set_mtime(round_dir / "dispatch-child.log", 200)
    _set_mtime(round_dir, 200)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "reviewers: 2/3 returned" in report


def test_design_step35_label_uses_generic_progress(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _write_design_mark(design, "Step 3.5 — plan review", ts=100)

    report = progress_report._render_design(_design_run(design))

    assert not progress_report._is_design_plan_review_step("Step 3.5 — plan review")
    assert report.startswith("design: Step 3.5 — plan review")


def test_design_step3b_label_uses_generic_progress(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _write_design_mark(design, "Step 3b — plan review", ts=100)

    report = progress_report._render_design(_design_run(design))

    assert not progress_report._is_design_plan_review_step("Step 3b — plan review")
    assert report.startswith("design: Step 3b — plan review")


def test_design_stale_manifest_outputs_ignore_glob_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    stale = _write_output(design / "slot-output.txt", 95)
    _write_output(round_dir / "unlisted-output.txt", 130)
    (round_dir / "round-start-s").write_text("90\n", encoding="utf-8")
    _write_slot_manifest(design / "plan-review-slots.ndjson", [stale])
    _set_mtime(design / "plan-review-slots.ndjson", 100)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "reviewers: 0/1 returned" in report


def test_design_stale_sidecar_is_ignored(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    stale = _write_output(design / "slot-output.txt", 95)
    retry = _write_output(design / "retry-output.txt", 130)
    (round_dir / "round-start-s").write_text("90\n", encoding="utf-8")
    manifest = design / "plan-review-slots.ndjson"
    _write_slot_manifest(manifest, [stale])
    _set_mtime(manifest, 100)
    sidecar = Path(f"{manifest}.output-files")
    sidecar.write_text(f"{retry}\n", encoding="utf-8")
    _set_mtime(sidecar, 99)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "reviewers: 0/1 returned" in report


def test_design_fresh_retry_sidecar_count_is_capped(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    stale_a = _write_output(design / "slot-a-output.txt", 95)
    stale_b = _write_output(design / "slot-b-output.txt", 95)
    retries = [
        _write_output(design / "retry-a-output.txt", 130),
        _write_output(design / "retry-b-output.txt", 130),
        _write_output(design / "retry-c-output.txt", 130),
    ]
    (round_dir / "round-start-s").write_text("90\n", encoding="utf-8")
    manifest = design / "plan-review-slots.ndjson"
    _write_slot_manifest(manifest, [stale_a, stale_b])
    _set_mtime(manifest, 100)
    sidecar = Path(f"{manifest}.output-files")
    sidecar.write_text("".join(f"{path}\n" for path in retries), encoding="utf-8")
    _set_mtime(sidecar, 120)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "reviewers: 2/2 returned" in report


def test_design_stale_root_manifest_from_prior_round_rejected(tmp_path: Path) -> None:
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 220)
    (round_dir / "round-start-s").write_text("200\n", encoding="utf-8")
    _write_slot_manifest(design / "plan-review-slots.ndjson", [out])
    _set_mtime(design / "plan-review-slots.ndjson", 100)

    assert progress_report._render_design_plan_review(design_tmpdir=design, start_s=200) == ""


def test_design_stale_root_manifest_before_round2_dispatch_rejected(tmp_path: Path) -> None:
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    stale = _write_output(design / "slot-output.txt", 150)
    _write_slot_manifest(design / "plan-review-slots.ndjson", [stale])
    _set_mtime(design / "plan-review-slots.ndjson", 180)
    _set_mtime(round_dir, 200)

    assert progress_report._render_design_plan_review(design_tmpdir=design, start_s=100) == ""


def test_design_round_start_contents_used_instead_of_file_mtime(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 250)
    round_start = round_dir / "round-start-s"
    round_start.write_text("200\n", encoding="utf-8")
    _set_mtime(round_start, 1000)
    _write_slot_manifest(design / "plan-review-slots.ndjson", [out])
    _set_mtime(design / "plan-review-slots.ndjson", 250)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=100)

    assert "reviewers: 1/1 returned" in report


def test_design_stale_round_local_manifest_rejected(tmp_path: Path) -> None:
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 120)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 90)

    assert progress_report._render_design_plan_review(design_tmpdir=design, start_s=100) == ""


def test_design_fresh_manifest_reused_stale_output_not_counted(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    stale = _write_output(design / "slot-output.txt", 80)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [stale])
    _set_mtime(round_dir / "panel-manifest.ndjson", 200)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=100)

    assert "reviewers: 0/1 returned" in report


def test_design_output_freshness_threshold_uses_parsed_round_start(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    too_old = _write_output(design / "slot-output.txt", 150)
    (round_dir / "round-start-s").write_text("200\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [too_old])
    _set_mtime(round_dir / "panel-manifest.ndjson", 300)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=100)

    assert "reviewers: 0/1 returned" in report


def test_design_round2_elapsed_uses_round_dir_mtime_without_round_start(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 220)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 170)
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 170)
    _set_mtime(round_dir, 160)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=100)

    assert "round 2 in progress" in report
    assert "elapsed: 1m" in report


def test_design_no_anchor_root_manifest_older_than_round_dir_rejected(tmp_path: Path) -> None:
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 220)
    _write_slot_manifest(design / "plan-review-slots.ndjson", [out])
    _set_mtime(design / "plan-review-slots.ndjson", 100)
    _set_mtime(round_dir, 200)

    assert progress_report._render_design_plan_review(design_tmpdir=design, start_s=None) == ""


def _write_voter_manifest(manifest: Path, outputs: list[Path]) -> None:
    """Write a plan-voter-slots.ndjson with voter-2/voter-3 entries."""
    manifest.parent.mkdir(parents=True, exist_ok=True)
    tools = ["codex", "cursor"]
    lines: list[str] = []
    for idx, (output, tool) in enumerate(zip(outputs, tools, strict=False), start=2):
        lines.append(f'{{"slot":"voter-{idx}","tool":"{tool}","output":"{output}"}}\n')
    manifest.write_text("".join(lines), encoding="utf-8")


def test_design_step3_voter_manifest_shows_vote_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    # Voter manifest written at ts=150 (after plan review mark at ts=90)
    codex_vote = design / "codex-vote-output.txt"
    _write_voter_manifest(design / "plan-voter-slots.ndjson", [codex_vote])
    _set_mtime(design / "plan-voter-slots.ndjson", 150)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "plan vote in progress" in report
    assert "voters:" in report
    assert "reviewers:" in report


def test_design_step3_voter_manifest_counts_returned_external_voter(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    codex_vote = _write_output(design / "codex-vote-output.txt", 200)
    cursor_vote = design / "cursor-vote-output.txt"  # not yet written
    _write_voter_manifest(design / "plan-voter-slots.ndjson", [codex_vote, cursor_vote])
    _set_mtime(design / "plan-voter-slots.ndjson", 150)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    # 1 external returned (codex), 0 Claude done, 0 cursor done → 1/(2+1)=1/3
    assert "voters: 1/3 returned" in report


def test_design_step3_voter_manifest_counts_claude_voter_done(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    _write_output(design / "claude-vote-output.txt", 180)
    codex_vote = design / "codex-vote-output.txt"
    cursor_vote = design / "cursor-vote-output.txt"
    _write_voter_manifest(design / "plan-voter-slots.ndjson", [codex_vote, cursor_vote])
    _set_mtime(design / "plan-voter-slots.ndjson", 150)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    # Claude done=1, 0 external done → 1/(2+1)=1/3
    assert "voters: 1/3 returned" in report


def test_design_step3_counts_claude_voter_done_before_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    _write_output(design / "claude-vote-output.txt", 140)
    codex_vote = design / "codex-vote-output.txt"
    cursor_vote = design / "cursor-vote-output.txt"
    _write_voter_manifest(design / "plan-voter-slots.ndjson", [codex_vote, cursor_vote])
    _set_mtime(design / "plan-voter-slots.ndjson", 150)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    # Claude may finish before the external voter manifest is written.
    assert "voters: 1/3 returned" in report


def test_design_step3_stale_voter_manifest_shows_reviewer_header(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    # Voter manifest at ts=80, stale vs step_start_s=90
    codex_vote = design / "codex-vote-output.txt"
    _write_voter_manifest(design / "plan-voter-slots.ndjson", [codex_vote])
    _set_mtime(design / "plan-voter-slots.ndjson", 80)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "plan vote in progress" not in report
    assert "round 1 in progress" in report
    assert "reviewers:" in report


def test_implement_stale_label_with_fresh_round_dir_triggers_step5(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Stale step label (Step 4) but fresh round-1 dir → _render_step5 fires with staleness note."""
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    _write_mark(impl, "Step 4 — commit implementation", ts=100)
    (round_dir / "round-start-s").write_text("110\n", encoding="utf-8")

    reported: list[str] = []

    def fake_step5(*, implement_tmpdir: Path, run_id: str = "", window_start_s: int | None = None) -> str:
        _ = run_id, window_start_s
        reported.append(str(implement_tmpdir))
        return "step5 detail"

    monkeypatch.setattr(progress_report, "_render_step5", fake_step5)

    report = progress_report._render_implement(
        progress_report.LiveRun("implement", impl, str(impl), impl / "pointer", 0)
    )

    assert reported, "staleness fallback should have called _render_step5"
    assert "step5 detail" in report
    assert "note: step marks stale; phase inferred from round artifacts" in report


def test_implement_stale_label_no_fresh_round_dir_falls_through(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Stale label (Step 4) and no round dir → generic report, no staleness note."""
    impl = tmp_path / "impl"
    impl.mkdir()
    _write_mark(impl, "Step 4 — commit implementation", ts=100)

    def fail_step5(**_kw: object) -> str:
        raise AssertionError("_render_step5 should not run without a round dir")

    monkeypatch.setattr(progress_report, "_render_step5", fail_step5)

    report = progress_report._render_implement(
        progress_report.LiveRun("implement", impl, str(impl), impl / "pointer", 0)
    )

    assert report.startswith("implement: Step 4 — commit implementation")
    assert "stale" not in report


def test_design_stale_label_with_fresh_round_dir_triggers_plan_review(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Stale design label (Step 2b) but fresh plan-review/round-1 → rich view fires with staleness note."""
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _write_design_mark(design, "design Step 2b — plan", ts=100)
    (round_dir / "round-start-s").write_text("110\n", encoding="utf-8")

    monkeypatch.setattr(
        progress_report, "_render_design_plan_review", lambda **_k: "rich plan review"
    )

    report = progress_report._render_design(_design_run(design))

    assert "rich plan review" in report
    assert "note: step marks stale; phase inferred from round artifacts" in report


def test_design_stale_label_no_fresh_round_dir_falls_through(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Stale design label and no round dir → generic report, no staleness note."""
    design = tmp_path / "design"
    design.mkdir()
    _write_design_mark(design, "design Step 2b — plan", ts=100)

    def fail_rich(**_kw: object) -> str:
        raise AssertionError("rich renderer should not run without a round dir")

    monkeypatch.setattr(progress_report, "_render_design_plan_review", fail_rich)

    report = progress_report._render_design(_design_run(design))

    assert report.startswith("design: design Step 2b — plan")
    assert "stale" not in report


# Item 4: auto-continuation entry matches _is_design_plan_review_step
def test_is_design_plan_review_step_matches_auto_continuation() -> None:
    assert progress_report._is_design_plan_review_step("design Step 3 — auto-continuation entry")


def test_is_design_plan_review_step_auto_continuation_fires_rich_renderer(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Round 2+ auto-continuation timing mark triggers rich plan review renderer (no stale note)."""
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    _write_design_mark(design, "design Step 3 — auto-continuation entry", ts=100)
    (round_dir / "round-start-s").write_text("110\n", encoding="utf-8")

    monkeypatch.setattr(
        progress_report, "_render_design_plan_review", lambda **_k: "rich plan review"
    )

    report = progress_report._render_design(_design_run(design))

    assert "rich plan review" in report
    assert "stale" not in report


# Item 1: stale voter manifest from prior round is rejected when round_dir is provided
def test_fresh_design_voter_manifest_stale_from_prior_round(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    (round_dir / "round-start-s").write_text("200\n", encoding="utf-8")
    manifest = design / "plan-voter-slots.ndjson"
    manifest.write_text('{"slot":"voter-2","tool":"codex","output":"/tmp/out.txt"}\n', encoding="utf-8")
    _set_mtime(manifest, 100)  # older than round start (200)

    result = progress_report._fresh_design_voter_manifest(design_tmpdir=design, step_start_s=90, round_dir=round_dir)

    assert result is None, "stale voter manifest should be rejected when round_dir is provided"


def test_fresh_design_voter_manifest_fresh_for_current_round(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    (round_dir / "round-start-s").write_text("150\n", encoding="utf-8")
    manifest = design / "plan-voter-slots.ndjson"
    manifest.write_text('{"slot":"voter-2","tool":"codex","output":"/tmp/out.txt"}\n', encoding="utf-8")
    _set_mtime(manifest, 200)  # newer than round start (150)

    result = progress_report._fresh_design_voter_manifest(design_tmpdir=design, step_start_s=90, round_dir=round_dir)

    assert result is not None, "fresh voter manifest should be returned"


def test_render_design_plan_review_stale_voter_from_prior_round_shows_reviewer_header(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Voter manifest from prior round is rejected; header shows reviewers-only view."""
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 230)
    (round_dir / "round-start-s").write_text("200\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 210)
    # Voter manifest at ts=100 — older than round start (200): stale from round 1
    codex_vote = design / "codex-vote-output.txt"
    _write_voter_manifest(design / "plan-voter-slots.ndjson", [codex_vote])
    _set_mtime(design / "plan-voter-slots.ndjson", 100)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "plan vote in progress" not in report
    assert "round 2 in progress" in report


# Item 3: "round N complete" only when returned >= total
def test_render_design_plan_review_incomplete_reviewers_shows_in_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """When reviewers not all returned, header says 'in progress' not 'complete'."""
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    # 2 reviewer slots but only 1 output returned
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    missing_out = design / "slot-2-output.txt"  # not yet written
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out, missing_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    codex_vote = _write_output(design / "codex-vote-output.txt", 200)
    _write_voter_manifest(design / "plan-voter-slots.ndjson", [codex_vote])
    _set_mtime(design / "plan-voter-slots.ndjson", 150)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "round 1 in progress" in report
    assert "plan vote in progress" in report
    assert "reviewers: 1/2" in report


def test_render_design_plan_review_all_reviewers_returned_shows_complete(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """When all reviewers returned, header says 'complete'."""
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    codex_vote = design / "codex-vote-output.txt"
    _write_voter_manifest(design / "plan-voter-slots.ndjson", [codex_vote])
    _set_mtime(design / "plan-voter-slots.ndjson", 150)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "round 1 complete" in report
    assert "plan vote in progress" in report


# Item 2: Claude-only voter (empty external voter manifest) shows voter progress
def test_render_design_plan_review_claude_only_voter_shows_progress(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """When voter manifest is empty but claude-vote-output.txt is fresh, show voter block."""
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    # No external voter manifest — claude-vote-output.txt is the only voter
    _write_output(design / "claude-vote-output.txt", 160)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "plan vote in progress" in report
    assert "voters: 1/1 returned" in report


def test_render_design_plan_review_claude_voter_not_yet_done(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Empty claude-vote-output.txt and no voter manifest → voters: 0/1 returned."""
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    # claude-vote-output.txt exists but is empty (not yet written)
    claude_vote = design / "claude-vote-output.txt"
    claude_vote.write_text("", encoding="utf-8")
    _set_mtime(claude_vote, 160)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "plan vote in progress" in report
    assert "voters: 0/1 returned" in report


def test_render_design_plan_review_stale_claude_vote_no_voter_block(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Stale claude-vote-output.txt (before step_start_s) and no voter manifest → no voter block."""
    monkeypatch.setattr(progress_report.time, "time", lambda: 300)
    monkeypatch.setattr(progress_report, "_render_design_review_detail", lambda _tmpdir: "")
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_out = _write_output(design / "slot-1-output.txt", 130)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [reviewer_out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 120)
    # claude-vote-output.txt at ts=80 — stale vs step_start_s=90
    claude_vote = design / "claude-vote-output.txt"
    _write_output(claude_vote, 80)

    report = progress_report._render_design_plan_review(design_tmpdir=design, start_s=90)

    assert "plan vote in progress" not in report
    assert "round 1 in progress" in report


def _write_round_meta(round_dir: Path, accepted: int = 2, rejected: int = 1, reviewers: int = 3, collector: str = "") -> None:
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": str(accepted),
                "REJECTED_COUNT": str(rejected),
                "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "1",
                "OOS_ACCEPTED_COUNT": "1",
                "OOS_REJECTED_COUNT": "1",
            },
            "summary": {"panel": {"total_slot_count": reviewers}},
            "collector": collector,
        }) + "\n",
        encoding="utf-8",
    )


def test_render_phase_detail_no_rounds(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    root.mkdir()
    assert progress_report.render_phase_detail(rounds_root=root, skill="implement") == "## Review Phase Detail\n\nNo review rounds completed.\n"


def test_render_phase_detail_table_top_failures_and_gantt(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    r1 = root / "round-1"
    collector = "TOOL=codex\nSTATUS=FAILED\nREVIEWER_FILE=codex-specialist-arch-output.txt\n"
    _write_round_meta(r1, collector=collector)
    _write_slot_manifest(r1 / "panel-manifest.ndjson", [r1 / "codex-specialist-arch-output.txt"])
    findings = tmp_path / "review-findings-full.jsonl"
    findings.write_text(
        '{"outcome":"accepted","round_num":1,"reviewer_slots":["codex-specialist-arch-output.txt"]}\n',
        encoding="utf-8",
    )
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(timing, "codex-specialist-arch-output.txt", 110, 190)
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing, findings_file=findings)
    assert "| 1 | 4 | 2 | 2 | 1 | 1m 40s | — | 3 |" in rendered
    assert "| **Total (round-sum)** | **4** | **2** | **2** | **1** | **1m 40s** | **—** | **3** |" in rendered
    assert "1. codex/slot-1 — 1" in rendered
    assert "**Reviewer slot failures**: 1" in rendered
    assert "- codex/slot-1: 1" in rendered
    assert "### Round 1 reviewer timing" in rendered
    # Issue #4882: round-meta without a canonical block emits no decomposition footnote (backward compat).
    assert "Finding decomposition (canonical, scope-aware)" not in rendered


def test_render_phase_detail_merges_collector_and_dynamic_dropped_failures(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "panel-manifest.ndjson").write_text(
        json.dumps(
            {
                "slot": "arch",
                "tool": "codex",
                "output": str(r1 / "codex-specialist-arch-output.txt"),
            }
        )
        + "\n"
        + json.dumps(
            {
                "slot": "dyn-dyn-lint-escalation",
                "tool": "cursor",
                "output": str(r1 / "dyn-dyn-lint-escalation-output.txt"),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "collector-results.env").write_text(
        f"REVIEWER_FILE={r1 / 'codex-specialist-arch-output.txt'}\n"
        "TOOL=codex\n"
        "STATUS=ERROR\n\n",
        encoding="utf-8",
    )
    (r1 / "panel-manifest.ndjson.output-files.dropped-slots").write_text(
        "dyn-dyn-lint-escalation\tcursor\tstraggler-dropped\tcut\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "**Reviewer slot failures**: 2" in rendered
    assert "- codex/arch: 1" in rendered
    assert "- cursor/dyn-dyn-lint-escalation: 1" in rendered


def test_render_phase_detail_treats_cap_hit_as_success(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "collector-results.env").write_text(
        "REVIEWER_FILE=codex-specialist-arch-output.txt\n"
        "TOOL=codex\n"
        "STATUS=cap_hit\n\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "**Reviewer slot failures**: 0" in rendered


def test_render_phase_detail_suppresses_dropped_row_when_collector_ok(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    r1 = root / "round-1"
    _write_round_meta(r1)
    output = r1 / "dyn-dyn-lint-escalation-output.txt"
    (r1 / "panel-manifest.ndjson").write_text(
        json.dumps(
            {
                "slot": "dyn-dyn-lint-escalation",
                "tool": "cursor",
                "output": str(output),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (r1 / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\n"
        "TOOL=cursor\n"
        "STATUS=OK\n\n",
        encoding="utf-8",
    )
    (r1 / "panel-manifest.ndjson.output-files.dropped-slots").write_text(
        "dyn-dyn-lint-escalation\tcursor\tstraggler-dropped\tcut\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "**Reviewer slot failures**: 0" in rendered


def test_render_phase_detail_ignores_stale_grandparent_collector_for_implement(tmp_path: Path) -> None:
    root = tmp_path / "impl"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (tmp_path / "collector-results.env").write_text(
        "REVIEWER_FILE=stale-output.txt\n"
        "TOOL=codex\n"
        "STATUS=ERROR\n\n",
        encoding="utf-8",
    )
    (r1 / "collector-results.env").write_text(
        "REVIEWER_FILE=good-output.txt\n"
        "TOOL=codex\n"
        "STATUS=OK\n\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "**Reviewer slot failures**: 0" in rendered


def test_render_phase_detail_shows_canonical_decomposition_footnote(tmp_path: Path) -> None:
    # Issue #4882: when round-meta carries the canonical decomposition, the table footnote reconciles
    # the raw "Suggestions" count with the in-scope headline (e.g. 18 raw -> 3 in-scope + 13 OOS).
    root = tmp_path / "review"
    r1 = root / "round-1"
    r1.mkdir(parents=True)
    (r1 / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": "0", "REJECTED_COUNT": "18", "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0", "OOS_ACCEPTED_COUNT": "0", "OOS_REJECTED_COUNT": "0",
            },
            "tally_canonical": {
                "ACCEPTED_COUNT": "0", "REJECTED_COUNT": "3", "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0", "OOS_ACCEPTED_COUNT": "0", "OOS_REJECTED_COUNT": "13",
            },
            "nit_pruned_count": "8",
            "summary": {"panel": {"total_slot_count": 3}},
            "collector": "",
        }) + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")
    # The Suggestions column still shows the raw round-sum (18) so no data is hidden.
    assert "| 1 | 18 | 0 |" in rendered
    # The decomposition footnote reconciles raw 18 with the in-scope 3 + 13 OOS (8 nit-pruned).
    assert "Finding decomposition (canonical, scope-aware)" in rendered
    assert "round 1: 16 finding(s) = 3 in-scope" in rendered
    assert "13 out-of-scope" in rendered
    assert "8 nit-pruned" in rendered
    assert "tally_canonical" in rendered


def test_render_phase_detail_dual_timing_windows(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="design", round_num=1, start_s=0, end_s=1800)
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(timing, "codex-specialist-arch-output.txt", 10, 500)
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)
    assert "1m 40s" in rendered
    assert "window 0:00-30:00 (1800s)" in rendered


def test_write_round_meta_helpers(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n| FINDING_2 | rejected |\n| OOS_1 | accepted |\n",
        encoding="utf-8",
    )
    (round_dir / "panel-manifest.ndjson").write_text('{"slot":"a","tool":"codex","output":"a.txt"}\n', encoding="utf-8")
    assert progress_report.write_implement_round_meta(round_dir) == 0
    meta = (round_dir / "round-meta.json").read_text(encoding="utf-8")
    assert '"ACCEPTED_COUNT": "1"' in meta
    assert '"OOS_ACCEPTED_COUNT": "1"' in meta
    assert '"total_slot_count": 1' in meta
    # Issue #4882: no classification TSV present, so only the raw tally is recorded (backward compat).
    assert "tally_canonical" not in meta


def test_write_implement_round_meta_records_canonical_decomposition(tmp_path: Path) -> None:
    # Issue #4882: a finding reclassified out-of-scope after voting keeps its FINDING_ id, so the raw
    # id-prefix tally over-counts it as in-scope rejected. write_implement_round_meta must also record
    # the canonical scope-aware split (from the classification TSV) plus the nit-pruned count.
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n"
        "| FINDING_1 | accepted |\n| FINDING_2 | rejected |\n| FINDING_3 | rejected |\n",
        encoding="utf-8",
    )
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, result: str, scope: str) -> str:
        cols = dict.fromkeys(header, "")
        cols.update({"finding_id": finding_id, "voting_result": result, "scope": scope})
        return "\t".join(cols[name] for name in header)

    # FINDING_3 voted rejected but is scope=oos: the raw tally counts it in-scope, canonical counts OOS.
    (round_dir / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "accepted", "in_scope") + "\n"
        + row("FINDING_2", "rejected", "in_scope") + "\n"
        + row("FINDING_3", "rejected", "oos") + "\n",
        encoding="utf-8",
    )
    (round_dir / "prune-nit.env").write_text("PRUNED_COUNT=1\nINSCOPE_REMAINING=2\n", encoding="utf-8")

    assert progress_report.write_implement_round_meta(round_dir) == 0
    meta = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))
    # Raw tally counts FINDING_3 by id-prefix as an in-scope rejection (the #4882 over-count).
    assert meta["tally"]["REJECTED_COUNT"] == "2"
    # Canonical (scope-aware) splits it out: 1 in-scope rejected, 1 OOS rejected.
    assert meta["tally_canonical"]["ACCEPTED_COUNT"] == "1"
    assert meta["tally_canonical"]["REJECTED_COUNT"] == "1"
    assert meta["tally_canonical"]["OOS_REJECTED_COUNT"] == "1"
    assert meta["nit_pruned_count"] == "1"


def test_write_design_round_meta_security_oos_and_panel(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| OOS_SEC | accepted |\n",
        encoding="utf-8",
    )
    (round_dir / "findings-oos.md").write_text(
        "### OOS_SEC: security item\nfocus-area=security\n",
        encoding="utf-8",
    )
    (round_dir / "plan-review-slots.ndjson").write_text(
        '{"slot":"slot-1","tool":"codex","output":"codex-out.txt"}\n',
        encoding="utf-8",
    )
    (round_dir / "round-summary.env").write_text("COLLECT_FAILURE_COUNT=2\n", encoding="utf-8")
    (round_dir / "revise").mkdir()
    (round_dir / "revise" / "revise.env").write_text("REVISE_STATUS=ok-fallback\nREVISE_TIER=primary\n", encoding="utf-8")
    monkeypatch.setattr(progress_report.voting, "is_security_block", lambda _path: True)
    assert progress_report.write_design_round_meta(round_dir) == 0
    meta = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))
    assert meta["tally"]["OOS_ACCEPTED_COUNT"] == "0"
    assert meta["summary"]["panel"]["total_slot_count"] == 1
    assert "collector-failure-1" in meta["collector"]
    assert meta["revise"]["status"] == "ok-fallback"
    assert meta["revise"]["tier"] == "primary"


def test_render_phase_detail_top_reviewers_from_classification(tmp_path: Path) -> None:
    # Issue #4733 Bug 1: /design records per-round attribution in findings-classification.tsv
    # but never emits review-findings-full.jsonl, so Top reviewers must aggregate from the TSV
    # (the same data behind the Reviewer Competition Scoreboard) instead of rendering empty.
    root = tmp_path / "plan-review"
    r1 = root / "round-1"
    _write_round_meta(r1)
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, reviewer: str, result: str, severity: str = "minor", scope: str = "in_scope") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": reviewer,
            "voting_result": result,
            "v1_vote": "YES" if result == "accepted" else "NO",
            "v1_severity": severity,
            "v2_vote": "YES" if result == "accepted" and severity in {"blocker", "major"} else "",
            "v2_severity": severity if result == "accepted" and severity in {"blocker", "major"} else "",
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "Cursor-Requirements", "accepted", "major") + "\n"
        + row("FINDING_2", "Cursor-Requirements", "accepted") + "\n"
        + row("FINDING_3", "Codex-Generic", "accepted") + "\n"
        + row("FINDING_4", "Codex-Generic", "rejected") + "\n"
        + row("OOS_1", "Cursor-Arch", "accepted", "major", "oos") + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    assert "1. Cursor-Requirements — 3" in rendered
    assert "2. Codex-Generic — 1" in rendered
    assert "- (no accepted-point score attributed to a reviewer slot)" not in rendered
    # OOS rows are excluded so Top reviewers matches the in-scope Accepted column.
    assert "Cursor-Arch" not in rendered


def test_render_phase_detail_top_reviewers_implement_from_classification(tmp_path: Path) -> None:
    root = tmp_path / "review"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "panel-manifest.ndjson").write_text(
        '{"slot":"arch","tool":"cursor","output":"cursor-specialist-arch-output.txt"}\n'
        '{"slot":"generalist","tool":"codex","output":"codex-generalist-output.txt"}\n',
        encoding="utf-8",
    )
    (root / "review-findings-full.jsonl").write_text(
        '{"outcome":"accepted","reviewer":"flat-jsonl-output.txt"}\n',
        encoding="utf-8",
    )
    header = progress_report.voting.code_review_classification_header().split("\t")

    def row(finding_id: str, reviewer: str, result: str, severity: str, scope: str) -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "reviewer_slots": reviewer,
            "voting_result": result,
            "v1_vote": "YES" if result == "accepted" else "NO",
            "v1_severity": severity,
            "v2_vote": "YES" if result == "accepted" and severity in {"blocker", "major"} else "",
            "v2_severity": severity if result == "accepted" and severity in {"blocker", "major"} else "",
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "cursor-specialist-arch-output.txt", "accepted", "major", "in_scope") + "\n"
        + row("FINDING_2", "codex-generalist-output.txt", "accepted", "minor", "in_scope") + "\n"
        + row("FINDING_3", "cursor-specialist-oos-output.txt", "accepted", "major", "oos") + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", findings_file=root / "review-findings-full.jsonl")
    assert "1. cursor/arch — 2" in rendered
    assert "2. codex/generalist — 1" in rendered
    assert "flat-jsonl" not in rendered
    assert "cursor-specialist-oos" not in rendered


def test_render_phase_detail_top_reviewers_implement_from_classification_vendor_fallback(
    tmp_path: Path,
) -> None:
    root = tmp_path / "review"
    r1 = root / "round-1"
    _write_round_meta(r1, accepted=1, rejected=0, reviewers=1)
    output = "cursor-specialist-arch-output.txt"
    (r1 / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "arch", "tool": "cursor", "output": output}) + "\n",
        encoding="utf-8",
    )
    (root / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\nTOOL=codex\nSTATUS=OK\n\n",
        encoding="utf-8",
    )
    header = progress_report.voting.code_review_classification_header().split("\t")
    cols = dict.fromkeys(header, "")
    cols.update({
        "finding_id": "FINDING_1",
        "reviewer_slots": output,
        "voting_result": "accepted",
        "v1_vote": "YES",
        "v1_severity": "minor",
        "scope": "in_scope",
    })
    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n" + "\t".join(cols[name] for name in header) + "\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert not (r1 / "collector-results.env").exists()
    assert "1. cursor/arch (via Codex) — 1" in rendered


def test_render_phase_detail_total_relabeled_round_sum_under_recurrence(tmp_path: Path) -> None:
    # Issue #4809: when the plan-review loop re-raises and re-accepts the same finding across
    # rounds (the #4808 non-convergence condition), the Total Suggestions/Accepted is a naive
    # per-round sum that exceeds the distinct-finding count, and Top reviewers inflates the same
    # way. The per-round artifacts carry no stable cross-round finding identity (only per-round
    # FINDING_N), so distinct-finding dedup is not reliably achievable; instead the Total stays a
    # round-sum but is labeled and captioned so it cannot be misread as a distinct-finding count.
    root = tmp_path / "plan-review"
    header = progress_report.voting.findings_classification_header().split("\t")
    cols = dict.fromkeys(header, "")
    cols.update({
        "finding_id": "FINDING_1",
        "finding_reviewers": "Cursor-Arch",
        "voting_result": "accepted",
        "v1_vote": "YES",
        "v1_severity": "minor",
        "scope": "in_scope",
    })
    line = "\t".join(cols[name] for name in header)
    for round_num in (1, 2, 3):
        round_dir = root / f"round-{round_num}"
        _write_round_meta(round_dir)
        # Identical single finding accepted every round: the #4808 recurrence signature.
        (round_dir / "findings-classification.tsv").write_text(
            "\t".join(header) + "\n" + line + "\n",
            encoding="utf-8",
        )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    # The Total row is explicitly labeled a round-sum, never a bare "Total" implying distinct work.
    assert "| **Total (round-sum)** |" in rendered
    assert "| **Total** |" not in rendered
    # The caption spells out the round-sum semantics so the inflated numbers cannot silently mislead.
    assert "round-sum" in rendered
    assert "counted once per round" in rendered
    # One finding accepted in all three rounds is counted once per round (round-sum => "— 3"),
    # not deduplicated to 1; the label and caption are what prevent misreading it as distinct work.
    assert "1. Cursor-Arch — 3" in rendered


def test_parse_classification_tsv_counts_neutral_oos(tmp_path: Path) -> None:
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, result: str, scope: str = "oos") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": "Cursor-Arch",
            "voting_result": result,
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    path = tmp_path / "findings-classification.tsv"
    path.write_text(
        "\t".join(header) + "\n"
        + row("OOS_1", "accepted") + "\n"
        + row("OOS_2", "neutral") + "\n"
        + row("OOS_3", "rejected") + "\n",
        encoding="utf-8",
    )
    accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected = progress_report._parse_classification_tsv(path)
    assert accepted == rejected == neutral == exonerated == 0
    assert oos_accepted == 1
    assert oos_rejected == 2


def test_top_reviewers_whitespace_coproposers_and_comma_fallback(tmp_path: Path) -> None:
    root = tmp_path / "plan-review"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "plan-review-prune-label-map.tsv").write_text(
        "slot\thuman_label\nplan-requirements\tCursor-Pragmatic\nplan-architecture\tCodex-Arch\n",
        encoding="utf-8",
    )
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, reviewer: str, result: str, severity: str = "major") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": reviewer,
            "voting_result": result,
            "v1_vote": "YES" if result == "accepted" else "NO",
            "v1_severity": severity,
            "v2_vote": "YES" if result == "accepted" and severity in {"blocker", "major"} else "",
            "v2_severity": severity if result == "accepted" and severity in {"blocker", "major"} else "",
            "scope": "in_scope",
        })
        return "\t".join(cols[name] for name in header)

    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "Cursor-Pragmatic Codex-Arch", "accepted") + "\n"
        + row("FINDING_2", "Unknown-Label", "accepted") + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    assert "1. Codex-Arch — 2" in rendered
    assert "2. Cursor-Pragmatic — 2" in rendered
    assert "3. Unknown-Label — 2" in rendered
    assert "Cursor-Pragmatic Codex-Arch" not in rendered


def test_top_reviewers_classification_unique_finder_bonus(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("LARCH_UNIQUE_FINDER_BONUS", "0.25")
    root = tmp_path / "plan-review"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "plan-review-prune-label-map.tsv").write_text(
        "slot\thuman_label\nplan-requirements\tCursor-Pragmatic\nplan-architecture\tCodex-Arch\n",
        encoding="utf-8",
    )
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, reviewer: str, scope: str = "in_scope") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": reviewer,
            "voting_result": "accepted",
            "v1_vote": "YES",
            "v1_severity": "minor",
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_SOLE", "Solo-Reviewer") + "\n"
        + row("FINDING_MULTI", "Multi-A, Multi-B") + "\n"
        + row("FINDING_WHITESPACE", "Cursor-Pragmatic Codex-Arch") + "\n"
        + row("OOS_1", "Oos-Reviewer", "oos") + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    assert "1. Solo-Reviewer — 1.25" in rendered
    assert "2. Codex-Arch — 1" in rendered
    assert "3. Cursor-Pragmatic — 1" in rendered
    assert "4. Multi-A — 1" in rendered
    assert "5. Multi-B — 1" in rendered
    assert "— 1.0" not in rendered
    assert "Oos-Reviewer" not in rendered


def test_write_design_round_meta_collector_from_real_records(tmp_path: Path) -> None:
    # Issue #4733 Bug 2: the collector field is built from real per-slot collector-results.env
    # records (KEY=VALUE blocks: REVIEWER_FILE/TOOL/STATUS/...), not count-based placeholders.
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n",
        encoding="utf-8",
    )
    (round_dir / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-requirements","tool":"cursor","output":"cursor-plan-requirements-output.txt"}\n',
        encoding="utf-8",
    )
    (round_dir / "round-summary.env").write_text("COLLECT_FAILURE_COUNT=1\n", encoding="utf-8")
    # collector-results.env is written at the design tmpdir root (round_dir.parent.parent).
    (design / "collector-results.env").write_text(
        "REVIEWER_FILE=ok-output.txt\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\nSTRUCTURED_SIDECAR=\nFAILURE_REASON=\n"
        "\n"
        "REVIEWER_FILE=cursor-plan-requirements-output.txt\nTOOL=cursor\nSTATUS=FAILED\nEXIT_CODE=1\nSTRUCTURED_SIDECAR=\nFAILURE_REASON=timeout\n",
        encoding="utf-8",
    )
    assert progress_report.write_design_round_meta(round_dir) == 0
    collector = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))["collector"]
    assert "TOOL=cursor" in collector
    assert "REVIEWER_FILE=cursor-plan-requirements-output.txt" in collector
    assert "collector-failure" not in collector
    assert "ok-output.txt" not in collector  # OK records are not failures.


def test_design_failure_label_resolves_real_slot_end_to_end(tmp_path: Path) -> None:
    # Issue #4733 Bug 2: a failed cursor-plan-requirements slot renders as cursor/...,
    # not unknown/collector-failure-N, once the writer emits real records.
    design = tmp_path
    root = design / "plan-review"
    round_dir = root / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n",
        encoding="utf-8",
    )
    (round_dir / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-requirements","tool":"cursor","output":"cursor-plan-requirements-output.txt"}\n',
        encoding="utf-8",
    )
    (round_dir / "round-summary.env").write_text("COLLECT_FAILURE_COUNT=1\n", encoding="utf-8")
    (design / "collector-results.env").write_text(
        "REVIEWER_FILE=cursor-plan-requirements-output.txt\nTOOL=cursor\nSTATUS=FAILED\nEXIT_CODE=1\nSTRUCTURED_SIDECAR=\nFAILURE_REASON=timeout\n",
        encoding="utf-8",
    )
    assert progress_report.write_design_round_meta(round_dir) == 0
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    assert "**Reviewer slot failures**: 1" in rendered
    assert "unknown/collector-failure" not in rendered
    assert "cursor/" in rendered


def test_render_phase_detail_gantt_includes_signal_vendor_rows(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(timing, "codex-output.txt", 120, 150, status="signal")
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)
    assert "## Review Phase Detail" in rendered
    assert "| 1 | 4 | 2 | 2 | 1 | 1m 40s | — | 3 |" in rendered
    assert "### Round 1 reviewer timing" in rendered
    assert "```" in rendered
    assert "codex/codex-review" in rendered
    assert "│" in rendered
    assert "█" in rendered
    assert "30s" in rendered
    assert "No reviewer timing tasks overlapped this round." not in rendered


def test_render_phase_detail_splits_gantt_per_attempt(tmp_path: Path) -> None:
    # Issue #5504: a stall recovery reruns round 1 in the same session, leaving two round rows
    # for round 1. The Gantt must render one section per attempt, each with its own tight
    # window, so each attempt's reviewers and post-aggregation probes stay next to their own
    # aggregator instead of intermixing across a single merged session-spanning window.
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200, attempt=1)
    _write_round_timing(timing, skill="implement", round_num=1, start_s=400, end_s=520, attempt=2)
    _write_vendor_timing(timing, "codex-specialist-correctness-output.txt", 110, 190)
    _write_vendor_timing(timing, "codex-specialist-edge-cases-output.txt", 410, 510)
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)
    assert "### Round 1 reviewer timing (attempt 1)" in rendered
    assert "### Round 1 reviewer timing (attempt 2)" in rendered
    # Each attempt renders its own tight window (100s, 120s), never the merged 100..520 span.
    assert "(100s)" in rendered
    assert "(120s)" in rendered
    assert "(420s)" not in rendered
    # The bare single-attempt header must not appear once a round is split per attempt.
    assert "### Round 1 reviewer timing\n" not in rendered


def test_render_phase_detail_single_attempt_keeps_bare_header(tmp_path: Path) -> None:
    # Issue #5504: an explicit attempt=1 (no rerun) renders the bare header identical to
    # pre-attempt ledgers, so the "(attempt N)" suffix shows up only when a round truly reran.
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200, attempt=1)
    _write_vendor_timing(timing, "codex-specialist-correctness-output.txt", 110, 190)
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)
    assert "### Round 1 reviewer timing\n" in rendered
    assert "(attempt 1)" not in rendered


def test_render_phase_detail_token_ledger_dual_window(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="design", round_num=1, start_s=0, end_s=1800)
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(timing, "codex-specialist-arch-output.txt", 10, 500)
    token_ledger = tmp_path / "tokens.jsonl"
    in_window_ts = datetime.fromtimestamp(150, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_window_ts = datetime.fromtimestamp(50, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    token_ledger.write_text(
        json.dumps({"type": "vendor", "vendor": "codex", "input": 1000, "output": 0, "cache_read": 0, "cache_create": 0, "ts": in_window_ts})
        + "\n"
        + json.dumps({"type": "vendor", "vendor": "codex", "input": 1_000_000, "output": 0, "cache_read": 0, "cache_create": 0, "ts": out_window_ts})
        + "\n",
        encoding="utf-8",
    )
    def fake_cost(argv: list[str], **_kwargs: object) -> str:
        tokens = "0"
        for index, arg in enumerate(argv[:-1]):
            if arg == "--codex-input-tokens":
                tokens = argv[index + 1]
                break
        return f"TOTAL_COST={tokens}\n"

    monkeypatch.setattr(progress_report.report_tokens_cost, "token_cost_from_args", fake_cost)
    rendered = progress_report.render_phase_detail(
        rounds_root=root,
        skill="implement",
        timing_ledger=timing,
        token_ledger=token_ledger,
    )
    assert "| 1 |" in rendered
    assert "$1000" in rendered
    assert "window 0:00-30:00 (1800s)" in rendered


def test_render_phase_detail_token_ledger_codex_mini_model_split(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # gpt-5.4-mini tokens must use --codex-mini-* flags, not --codex-* (gpt-5.5 rates).
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    token_ledger = tmp_path / "tokens.jsonl"
    in_window_ts = datetime.fromtimestamp(150, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    token_ledger.write_text(
        json.dumps({"type": "vendor", "vendor": "codex", "model": "gpt-5.5", "input": 1000, "output": 0, "cache_read": 0, "cache_create": 0, "ts": in_window_ts})
        + "\n"
        + json.dumps({"type": "vendor", "vendor": "codex", "model": "gpt-5.4-mini", "input": 0, "output": 2000, "cache_read": 0, "cache_create": 0, "ts": in_window_ts})
        + "\n",
        encoding="utf-8",
    )
    captured: dict[str, list[str]] = {}

    def fake_cost(argv: list[str], **_kwargs: object) -> str:
        captured["argv"] = list(argv)
        return "TOTAL_COST=0.00\n"

    monkeypatch.setattr(progress_report.report_tokens_cost, "token_cost_from_args", fake_cost)
    progress_report.render_phase_detail(
        rounds_root=root,
        skill="implement",
        timing_ledger=timing,
        token_ledger=token_ledger,
    )
    argv = captured.get("argv", [])
    # gpt-5.5 tokens go to --codex-input-tokens / --codex-output-tokens
    assert "--codex-input-tokens" in argv
    i = argv.index("--codex-input-tokens")
    assert argv[i + 1] == "1000"
    assert "--codex-output-tokens" in argv
    o = argv.index("--codex-output-tokens")
    assert argv[o + 1] == "0"
    # gpt-5.4-mini tokens go to --codex-mini-* flags, not lumped into gpt-5.5
    assert "--codex-mini-output-tokens" in argv
    mo = argv.index("--codex-mini-output-tokens")
    assert argv[mo + 1] == "2000"


def test_render_phase_detail_best_effort_timeout(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Block the core renderer past the wall-clock budget via a real Event wait
    # (conftest no-ops time.sleep, so a sleep-based block would not actually block).
    release = threading.Event()

    def blocking_render(*_args: object, **_kwargs: object) -> str:
        release.wait(timeout=10)
        return "should never be returned"

    monkeypatch.setattr(progress_report, "render_phase_detail", blocking_render)
    monkeypatch.setattr(progress_report, "RENDER_PHASE_DETAIL_TIMEOUT_SECONDS", 0.05)
    try:
        assert progress_report._render_phase_detail_best_effort(Path("/missing"), skill="implement") == ""
    finally:
        release.set()


def test_write_implement_round_meta_records_difficulty(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    (round_dir / "review-tally.env").write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nNEUTRAL_COUNT=0\nEXONERATED_COUNT=0\n", encoding="utf-8")
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "dyn-risk", "tool": "codex", "output": "out.txt", "vendor": "codex", "resolved_model": "gpt"}) + "\n",
        encoding="utf-8",
    )
    (round_dir / "scout-difficulty-rating.raw.json").write_text(
        json.dumps({"predicted_tier": "TRIVIAL", "confidence": "low", "rationale": "unclear small diff"}) + "\n",
        encoding="utf-8",
    )

    assert progress_report.write_implement_round_meta(round_dir) == 0
    data = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))

    assert data["difficulty"]["tier_in_effect"] == "MODERATE"
    assert data["difficulty"]["scout"]["confidence"] == "low"


def test_materialize_design_panel_manifest_keeps_model_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (tmp_path / "plan-review-slots.ndjson").write_text(
        json.dumps({"slot": "arch", "tool": "cursor", "output": "arch.txt", "vendor": "cursor", "resolved_model": "cursor-model"}) + "\n",
        encoding="utf-8",
    )

    assert progress_report._materialize_design_panel_manifest(round_dir) == 1
    row = json.loads((round_dir / "panel-manifest.ndjson").read_text(encoding="utf-8"))

    assert row["vendor"] == "cursor"
    assert row["resolved_model"] == "cursor-model"
