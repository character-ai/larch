from __future__ import annotations
# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportMissingParameterType=false, reportUnknownParameterType=false

import os
import time
from pathlib import Path
from typing import cast

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


def _write_design_mark(tmpdir: Path, label: str, ts: int = 100) -> None:
    (tmpdir / "timing-ledger.tsv").write_text(
        f"v1\tmark\t{ts}\tdesign\t{label}\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
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
) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0, end_s - start_s)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(
            f"v1\tround\t{start_s}\t{skill}\t-\t{round_num}\t{start_s}\t{end_s}\t"
            f"{duration}\t0\t0\t0\t-\n"
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

    def fake_step5(implement_tmpdir: Path, run_id: str, start_s: int | None = None) -> str:
        called.append(implement_tmpdir)
        assert run_id == ""
        assert start_s == 100
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

    def fake_step5(implement_tmpdir: Path, run_id: str, start_s: int | None = None) -> str:
        rendered.append(implement_tmpdir)
        assert run_id == ""
        assert start_s == 20
        return "active step5 report"

    monkeypatch.setattr(progress_report, "_render_step5", fake_step5)

    report = progress_report._report(str(cwd))

    assert report == "active step5 report"
    assert rendered == [active_impl]


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
    (round_dir / "round-meta.json").write_text(_MINIMAL_ROUND_META, encoding="utf-8")
    start_s = int(time.time()) - 125
    (round_dir / "round-start-s").write_text(f"{start_s}\n", encoding="utf-8")
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda _tmpdir, _run_id: "detail")

    report = progress_report._render_step5(impl, "run-1")

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
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda _tmpdir, _run_id: "detail")

    report = progress_report._render_step5(impl, "run-1")

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

    assert progress_report._review_rounds_root(impl, run_id) == flushed.parent
    report = progress_report._render_step5(impl, run_id)
    assert "round 2 in progress" in report


def test_render_review_detail_argv(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    run_id = "run-1"
    flushed = impl / "larch-logs" / "implement" / run_id / "round-1"
    flushed.mkdir(parents=True)
    (flushed / "review-and-fix.env").write_text("", encoding="utf-8")
    (impl / "timing-ledger.tsv").write_text("v1\tmark\t1\timplement\tStep 5\t-\t-\t-\t-\t-\t-\t-\t-\n", encoding="utf-8")
    captured: list[tuple[list[str], int]] = []

    def fake_run(argv: list[str], **kwargs: object):  # type: ignore[no-untyped-def]
        captured.append((list(argv), cast("int", kwargs.get("timeout"))))

        class Result:
            returncode = 0
            stdout = "detail-table"
            stderr = ""

        return Result()

    monkeypatch.setattr(progress_report.subprocess, "run", fake_run)

    detail = progress_report._render_review_detail(impl, run_id)

    assert detail == "detail-table"
    assert captured
    argv, timeout = captured[0]
    assert "--rounds-root" in argv
    rounds_root = argv[argv.index("--rounds-root") + 1]
    assert rounds_root == str(flushed.parent)
    assert "--timing-ledger" in argv
    assert "--skill" in argv
    assert argv[argv.index("--skill") + 1] == "implement"
    assert "--no-gantt" not in argv
    assert timeout == progress_report.RENDER_PHASE_DETAIL_TIMEOUT_SECONDS
    assert timeout > 6


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

    def fake_run(_argv: list[str], **_kwargs: object):  # type: ignore[no-untyped-def]
        class Result:
            returncode = 0
            stdout = md_output

        return Result()

    monkeypatch.setattr(progress_report.subprocess, "run", fake_run)

    detail = progress_report._render_review_detail(impl, run_id)

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
    assert progress_report._derive_progress_label("aggregator-output.txt") == "aggregator"
    assert progress_report._derive_progress_label("scout-plan-manifest.json.raw") == "scout"
    assert (
        progress_report._derive_progress_label(
            "codex-output.txt",
            "codex",
            "codex-plan-autofix",
        )
        == "codex/apply"
    )
    assert (
        progress_report._derive_progress_label(
            "cursor-output.txt",
            "cursor",
            "cursor-plan-autofix",
        )
        == "cursor/apply"
    )
    assert progress_report._derive_progress_label("coder-codex.log", "codex", "codex-review-fix") == "codex/apply"
    assert progress_report._derive_progress_label("coder-cursor.log", "cursor", "cursor-review-fix") == "cursor/apply"

    output = tmp_path / "codex-output.txt"
    manifest = tmp_path / "panel-manifest.ndjson"
    manifest.write_text(f'{{"slot":"mapped","tool":"tool","output":"{output}"}}\n', encoding="utf-8")
    label_map = progress_report._progress_label_map_from_manifests([manifest])
    assert progress_report._derive_progress_label(str(output), "codex", "codex-plan-autofix", label_map) == "codex/apply"


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

    rows = progress_report._progress_vendor_rows(ledger, 100, 200, {})

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

    rows = progress_report._progress_vendor_rows(ledger, 100, 200, {}, skip_ci=True)

    assert len(rows) == 1
    assert rows[0].label == "codex/correctness"


def test_render_step5_inflight_only_skips_detail(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")

    def fail_detail(_tmpdir: Path, _run_id: str) -> str:
        raise AssertionError("_render_review_detail must not run for inflight-only root")

    monkeypatch.setattr(progress_report, "_render_review_detail", fail_detail)

    report = progress_report._render_step5(impl, "run-1")

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

    report = progress_report._render_step5(impl, "run-1")

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

    report = progress_report._render_step5(impl, "run-1", 100)

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
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda _t, _r: "sentinel-detail")

    report = progress_report._render_step5(impl, "run-1")

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
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda _t, _r: "completed-detail")

    report = progress_report._render_step5(impl, "run-1")

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
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda _tmpdir, _run_id: "completed-detail")

    report = progress_report._render_step5(impl, "run-1", 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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
    monkeypatch.setattr(progress_report, "_render_review_detail", lambda _tmpdir, _run_id: "completed-detail")

    report = progress_report._render_step5(impl, "run-1", 90)

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

    report = progress_report._render_step5(impl, "run-1")

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

    report = progress_report._render_step5(impl, "run-1")

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

    report = progress_report._render_design_plan_review(design, 90)

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

    def fake_run(_argv: list[str], **_kwargs: object):  # type: ignore[no-untyped-def]
        class Result:
            returncode = 0
            stdout = "## Review Phase Detail\n\n| Round |\n|--:|\n| **1** |\n"

        return Result()

    monkeypatch.setattr(progress_report.subprocess, "run", fake_run)

    report = progress_report._render_design_plan_review(design, 90)

    assert "Review Phase Detail" in report
    assert "## " not in report
    assert "|--:" not in report
    assert "**" not in report


def test_design_step3_label_triggers_rich_view(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    design = tmp_path / "design"
    design.mkdir()
    _write_design_mark(design, "Step 3 — plan review", ts=100)

    monkeypatch.setattr(progress_report, "_render_design_plan_review", lambda _tmpdir, _start_s: "rich")

    assert progress_report._render_design(_design_run(design)) == "rich"


def test_design_non_step3_label_skips_rich_view(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    design = tmp_path / "design"
    design.mkdir()
    _write_design_mark(design, "Step 2 — planning", ts=100)

    def fail_rich(_tmpdir: Path, _start_s: int | None) -> str:
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
    captured: list[tuple[list[str], int]] = []

    def fake_run(argv: list[str], **kwargs: object):  # type: ignore[no-untyped-def]
        captured.append((list(argv), cast("int", kwargs.get("timeout"))))

        class Result:
            returncode = 0
            stdout = "detail"

        return Result()

    monkeypatch.setattr(progress_report.subprocess, "run", fake_run)

    detail = progress_report._render_design_review_detail(design)

    assert detail == "detail"
    argv, timeout = captured[0]
    assert argv[argv.index("--skill") + 1] == "design"
    assert argv[argv.index("--rounds-root") + 1] == str(design / "plan-review")
    assert "--timing-ledger" in argv
    assert "--no-gantt" not in argv
    assert timeout == progress_report.RENDER_PHASE_DETAIL_TIMEOUT_SECONDS
    assert timeout > 6


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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

    assert "reviewers: 2/2 returned" in report


def test_design_stale_root_manifest_from_prior_round_rejected(tmp_path: Path) -> None:
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 220)
    (round_dir / "round-start-s").write_text("200\n", encoding="utf-8")
    _write_slot_manifest(design / "plan-review-slots.ndjson", [out])
    _set_mtime(design / "plan-review-slots.ndjson", 100)

    assert progress_report._render_design_plan_review(design, 200) == ""


def test_design_stale_root_manifest_before_round2_dispatch_rejected(tmp_path: Path) -> None:
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    stale = _write_output(design / "slot-output.txt", 150)
    _write_slot_manifest(design / "plan-review-slots.ndjson", [stale])
    _set_mtime(design / "plan-review-slots.ndjson", 180)
    _set_mtime(round_dir, 200)

    assert progress_report._render_design_plan_review(design, 100) == ""


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

    report = progress_report._render_design_plan_review(design, 100)

    assert "reviewers: 1/1 returned" in report


def test_design_stale_round_local_manifest_rejected(tmp_path: Path) -> None:
    design = tmp_path / "design"
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    out = _write_output(design / "slot-output.txt", 120)
    (round_dir / "round-start-s").write_text("100\n", encoding="utf-8")
    _write_slot_manifest(round_dir / "panel-manifest.ndjson", [out])
    _set_mtime(round_dir / "panel-manifest.ndjson", 90)

    assert progress_report._render_design_plan_review(design, 100) == ""


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

    report = progress_report._render_design_plan_review(design, 100)

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

    report = progress_report._render_design_plan_review(design, 100)

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

    report = progress_report._render_design_plan_review(design, 100)

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

    assert progress_report._render_design_plan_review(design, None) == ""


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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    def fake_step5(implement_tmpdir: Path, _run_id: str, _start_s: int | None = None) -> str:
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

    def fail_step5(_tmpdir: Path, _run_id: str, _start_s: int | None = None) -> str:
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
        progress_report, "_render_design_plan_review", lambda _tmpdir, _start_s: "rich plan review"
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

    def fail_rich(_tmpdir: Path, _start_s: int | None) -> str:
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
        progress_report, "_render_design_plan_review", lambda _tmpdir, _start_s: "rich plan review"
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

    result = progress_report._fresh_design_voter_manifest(design, step_start_s=90, round_dir=round_dir)

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

    result = progress_report._fresh_design_voter_manifest(design, step_start_s=90, round_dir=round_dir)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

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

    report = progress_report._render_design_plan_review(design, 90)

    assert "plan vote in progress" not in report
    assert "round 1 in progress" in report
