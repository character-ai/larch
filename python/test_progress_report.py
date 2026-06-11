from __future__ import annotations
# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportMissingParameterType=false, reportUnknownParameterType=false

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


def test_step5_between_rounds_keeps_latest_round_liveness(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    impl = tmp_path / "impl"
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "review-and-fix.env").write_text("STATUS=complete\n", encoding="utf-8")
    (round_dir / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
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
    captured: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object):  # type: ignore[no-untyped-def]
        captured.append(list(argv))

        class Result:
            returncode = 0
            stdout = "detail-table"
            stderr = ""

        return Result()

    monkeypatch.setattr(progress_report.subprocess, "run", fake_run)

    detail = progress_report._render_review_detail(impl, run_id)

    assert detail == "detail-table"
    assert captured
    argv = captured[0]
    assert "--rounds-root" in argv
    rounds_root = argv[argv.index("--rounds-root") + 1]
    assert rounds_root == str(flushed.parent)
    assert "--timing-ledger" in argv
    assert "--skill" in argv
    assert argv[argv.index("--skill") + 1] == "implement"


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
    captured: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object):  # type: ignore[no-untyped-def]
        captured.append(list(argv))

        class Result:
            returncode = 0
            stdout = "detail"

        return Result()

    monkeypatch.setattr(progress_report.subprocess, "run", fake_run)

    detail = progress_report._render_design_review_detail(design)

    assert detail == "detail"
    argv = captured[0]
    assert argv[argv.index("--skill") + 1] == "design"
    assert argv[argv.index("--rounds-root") + 1] == str(design / "plan-review")
    assert "--timing-ledger" in argv


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
