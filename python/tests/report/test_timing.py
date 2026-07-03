"""Tests for timing.py."""

from __future__ import annotations

import fcntl as fcntl_mod
import os
import stat
from pathlib import Path

import pytest

from larch.report import timing


def test_timing_vendor_task_accepts_claude_and_basename(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).record_vendor_task(
        vendor="claude",
        task_kind="claude-review",
        start_s=10,
        end_s=15,
        output="/tmp/secret/out.txt",
    )
    text = ledger.read_text(encoding="utf-8")
    assert "\tclaude\tclaude-review\t" in text
    assert "\tout.txt\t" in text
    assert "/tmp/secret" not in text


def test_timing_vendor_task_accepts_gate_b_apply(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger, skill="design").record_vendor_task(
        vendor="claude",
        task_kind="gate-b-apply",
        start_s=20,
        end_s=35,
        output="gate-b-apply-round-1.out",
    )
    assert "unknown task-kind" not in capsys.readouterr().err
    row = ledger.read_text(encoding="utf-8").strip().split("\t")
    assert row[0:2] == ["v1", "vendor"]
    assert row[3] == "design"
    assert row[5:11] == ["claude", "gate-b-apply", "20", "35", "15", "gate-b-apply-round-1.out"]


def test_timing_report_design_omits_workflow_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text(
        "v1\tmark\t10\tdesign\tdesign Step 0\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LARCH_TIMING_SKILL", "design")
    monkeypatch.setenv("LARCH_TEST_TIMING_NOW", "30")
    data = timing.TimingReport(ledger).render_json()
    assert "workflow_path" not in data


def test_timing_report_json_and_design_totals(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text(
        "v1\tmark\t10\tdesign\tdesign Step 0\t-\t-\t-\t-\t-\t-\t-\t-\n"
        "v1\tmark\t20\tdesign\tdesign Step 1\t-\t-\t-\t-\t-\t-\t-\t-\n"
        "v1\tvendor\t18\tdesign\t-\tcodex\tcodex-review\t11\t18\t7\tout.log\t0\tcomplete\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LARCH_TIMING_SKILL", "design")
    monkeypatch.setenv("LARCH_TEST_TIMING_NOW", "30")
    data = timing.TimingReport(ledger).render_json()
    assert "workflow_path" not in data
    assert data["total_seconds"] == 10
    assert data["vendor_task_averages"]


def test_timing_rejects_symlink_ledger(tmp_path: Path) -> None:
    target = tmp_path / "target.tsv"
    _ = target.write_text("", encoding="utf-8")
    link = tmp_path / "link.tsv"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        timing.TimingLedger(link).mark("bad")


def test_timing_rejects_non_regular_ledger(tmp_path: Path) -> None:
    fifo = tmp_path / "fifo"
    if hasattr(stat, "S_IFIFO"):
        os.mkfifo(fifo)
        with pytest.raises(ValueError, match="not a regular file"):
            timing.TimingLedger(fifo).mark("bad")


def test_timing_summary_counts_vendors_by_end_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text(
        "v1\tmark\t20\timplement\tStep 0\t-\t-\t-\t-\t-\t-\t-\t-\n"
        "v1\tvendor\t30\timplement\t-\tcodex\tcodex-review\t5\t15\t10\tout.log\t0\tcomplete\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LARCH_TIMING_SKILL", "implement")
    monkeypatch.setenv("LARCH_TEST_TIMING_NOW", "100")
    summary = timing.TimingReport(ledger).render(mode="summary")
    assert "vendor-tasks=0" in summary


def test_timing_replace_block_ignores_prose_marker_mentions(tmp_path: Path) -> None:
    target = tmp_path / "body.md"
    _ = target.write_text(
        "See <!-- timing-report-begin --> in docs\n\n"
        "<!-- timing-report-begin -->\nold\n<!-- timing-report-end -->\n",
        encoding="utf-8",
    )
    timing._replace_block(target=target, block="BLOCK\n")  # pyright: ignore[reportPrivateUsage]
    text = target.read_text(encoding="utf-8")
    assert "See <!-- timing-report-begin --> in docs" in text
    assert "BLOCK" in text
    assert "old" not in text


def test_timing_ledger_record_round_clamps_negative_duration(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).record_round(
        skill="design",
        step="design Step 3 — plan review",
        round_n=2,
        start_s=50,
        end_s=45,
        accepted=0,
        rejected=1,
        oos=4,
    )
    row = next(line for line in ledger.read_text(encoding="utf-8").splitlines() if "\tround\t" in line)
    parts = row.split("\t")
    assert parts[8] == "0"
    assert parts[11] == "4"


def test_timing_ledger_record_round_writes_incrementing_attempt(tmp_path: Path) -> None:
    # Issue #5504: a stall recovery reruns the same round in one session; each rerun must
    # record a distinct 1-based attempt index in the reserved trailing column so the progress
    # report can split the Gantt per attempt instead of merging both windows into one span.
    ledger = tmp_path / "timing-ledger.tsv"
    led = timing.TimingLedger(ledger)
    led.record_round(skill="implement", step="Step 5 — code review", round_n=1, start_s=100, end_s=200, accepted=1, rejected=0)
    led.record_round(skill="implement", step="Step 5 — code review", round_n=1, start_s=300, end_s=400, accepted=2, rejected=1)
    led.record_round(skill="implement", step="Step 5 — code review", round_n=2, start_s=500, end_s=600, accepted=0, rejected=0)
    rounds = [line.split("\t") for line in ledger.read_text(encoding="utf-8").splitlines() if "\tround\t" in line]
    # Two attempts for round 1, then round 2 restarts the counter at 1.
    assert [parts[5] for parts in rounds] == ["1", "1", "2"]
    assert [parts[12] for parts in rounds] == ["1", "2", "1"]
    # The attempt index reuses the reserved column, so the parser's fixed 13-column width holds.
    assert all(len(parts) == 13 for parts in rounds)


def test_timing_report_unknown_format_raises(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text("v1\tmark\t1\timplement\tStep 0\t-\t-\t-\t-\t-\t-\t-\t-\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown format"):
        _ = timing.TimingReport(ledger).render(mode="full", fmt="yaml")


def test_timing_report_implement_hides_workflow_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text(
        "v1\tmark\t0\timplement\tStep 1 — design plan\t-\t-\t-\t-\t-\t-\t-\t-\n"
        "v1\tmark\t10\timplement\tStep 2 — implementation\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LARCH_TIMING_SKILL", "implement")
    monkeypatch.setenv("LARCH_TEST_TIMING_NOW", "100")
    markdown = timing.TimingReport(ledger).render(mode="full", fmt="markdown")
    assert "**Workflow path**:" not in markdown
    data = timing.TimingReport(ledger).render_json()
    assert "workflow_path" not in data


def test_timing_harness_mark_missing_executable_emits_sentinel(capsys: pytest.CaptureFixture[str]) -> None:
    rc = timing.harness_mark(label="smoke", argv=["does-not-exist"])
    assert rc == 127
    out = capsys.readouterr().out.strip()
    assert out.startswith("LARCH_HARNESS_TIMING\tsmoke\t")
    assert out.endswith("s")


def test_timing_telemetry_mark_rejects_missing_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert timing.timing_telemetry_mark_main(["--label", "noop"]) == 0
    assert timing.timing_telemetry_mark_main(["--implement-tmpdir", "", "--label", "noop"]) == 0
    assert timing.timing_telemetry_mark_main(["--implement-tmpdir", "relative", "--label", "noop"]) == 0


def test_timing_harness_mark_runs_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script = tmp_path / "ok.sh"
    _ = script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    rc = timing.harness_mark(label="fixture", argv=["bash", str(script)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("LARCH_HARNESS_TIMING\tfixture\t")
    assert out.endswith("s")

    fail_script = tmp_path / "fail.sh"
    _ = fail_script.write_text("#!/usr/bin/env bash\nexit 42\n", encoding="utf-8")
    fail_script.chmod(0o755)
    rc_fail = timing.harness_mark(label="fail-fixture", argv=["bash", str(fail_script)])
    assert rc_fail == 42
    fail_out = capsys.readouterr().out.strip()
    assert fail_out.startswith("LARCH_HARNESS_TIMING\tfail-fixture\t")
    assert fail_out.endswith("s")


def test_timing_mark_if_latest_differs_appends_on_differing_label(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text(
        "v1\tmark\t10\timplement\tStep 4 — commit\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LARCH_TIMING_LEDGER", str(ledger))
    monkeypatch.setenv("LARCH_TIMING_SKILL", "implement")
    rc = timing.timing_mark_main(["--if-latest-differs", "Step 5 — code review"])
    assert rc == 0
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if "\tmark\t" in line]
    assert len(rows) == 2
    assert rows[-1].split("\t")[4] == "Step 5 — code review"


def test_timing_mark_if_latest_differs_skips_on_identical_label(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text(
        "v1\tmark\t10\timplement\tStep 5 — code review\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LARCH_TIMING_LEDGER", str(ledger))
    monkeypatch.setenv("LARCH_TIMING_SKILL", "implement")
    rc = timing.timing_mark_main(["--if-latest-differs", "Step 5 — code review"])
    assert rc == 0
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if "\tmark\t" in line]
    assert len(rows) == 1


def test_timing_mark_if_latest_differs_appends_on_empty_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    monkeypatch.setenv("LARCH_TIMING_LEDGER", str(ledger))
    monkeypatch.setenv("LARCH_TIMING_SKILL", "implement")
    rc = timing.timing_mark_main(["--if-latest-differs", "Step 5 — code review"])
    assert rc == 0
    assert ledger.is_file()
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if "\tmark\t" in line]
    assert len(rows) == 1
    assert rows[0].split("\t")[4] == "Step 5 — code review"


def test_timing_mark_main_catches_invalid_ledger(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fifo = tmp_path / "fifo.tsv"
    if hasattr(stat, "S_IFIFO"):
        os.mkfifo(fifo)
        rc = timing.timing_mark_main(["--ledger", str(fifo), "Step 0"])
        assert rc == 1
        assert "not a regular file" in capsys.readouterr().err


def test_validate_ledger_path_rejects_symlink_escape_before_mkdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    link = allowed / "link"
    link.symlink_to(outside)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    with pytest.raises(ValueError, match="not under an allowed root"):
        _ = timing.validate_ledger_path(str(link / "nested" / "timing-ledger.tsv"), env={"TMPDIR": str(allowed)})
    assert not (outside / "nested").exists()


def test_timing_record_vendor_task_rejects_invalid_vendor(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    with pytest.raises(ValueError, match="vendor must be codex"):
        timing.TimingLedger(ledger).record_vendor_task(
            vendor="gemini",
            task_kind="vendor-misc",
            start_s=1,
            end_s=2,
            output="x.log",
        )


def test_timing_record_vendor_task_warns_unknown_task_kind(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).record_vendor_task(
        vendor="codex",
        task_kind="totally-unknown-kind",
        start_s=1,
        end_s=2,
        output="x.log",
    )
    assert "unknown task-kind" in capsys.readouterr().err


@pytest.mark.parametrize("task_kind", ["codex-ci", "cursor-ci", "claude-ci"])
def test_timing_record_vendor_task_accepts_live_ci_task_kinds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    task_kind: str,
) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    vendor = task_kind.split("-", 1)[0]
    timing.TimingLedger(ledger).record_vendor_task(
        vendor=vendor,
        task_kind=task_kind,
        start_s=1,
        end_s=2,
        output="ci.out",
    )
    assert "unknown task-kind" not in capsys.readouterr().err


@pytest.mark.parametrize("task_kind", ["codex-review-fix", "cursor-review-fix", "claude-review-fix"])
def test_timing_record_vendor_task_accepts_review_fix_task_kinds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    task_kind: str,
) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    vendor = task_kind.split("-", 1)[0]
    timing.TimingLedger(ledger).record_vendor_task(
        vendor=vendor,
        task_kind=task_kind,
        start_s=1,
        end_s=2,
        output=f"{vendor}-apply.log",
    )
    assert "unknown task-kind" not in capsys.readouterr().err


@pytest.mark.parametrize("task_kind", ["claude-relevant-checks", "claude-lint-fix"])
def test_timing_record_vendor_task_accepts_checks_task_kinds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    task_kind: str,
) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).record_vendor_task(
        vendor="claude",
        task_kind=task_kind,
        start_s=1,
        end_s=2,
        output=f"{task_kind}.txt",
    )
    assert "unknown task-kind" not in capsys.readouterr().err


def test_timing_record_vendor_task_normalizes_status_aliases(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    for status, _expected in (("OK", "complete"), ("ERROR", "signal"), ("TIMEOUT", "signal")):
        timing.TimingLedger(ledger).record_vendor_task(
            vendor="codex",
            task_kind="codex-review",
            start_s=1,
            end_s=2,
            output="x.log",
            status=status,
        )
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if "\tvendor\t" in line]
    assert [row.split("\t")[-1] for row in rows] == ["complete", "signal", "signal"]


def test_timing_record_vendor_task_main_skips_ledger_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_record_vendor_task(_self: timing.TimingLedger, **_kwargs: object) -> None:
        raise PermissionError("blocked ledger")

    monkeypatch.setattr(timing.TimingLedger, "record_vendor_task", fail_record_vendor_task)
    rc = timing.timing_record_vendor_task_main([
        "--ledger",
        str(tmp_path / "timing-ledger.tsv"),
        "--vendor",
        "claude",
        "--task-kind",
        "claude-review",
        "--start-s",
        "1",
        "--end-s",
        "2",
        "--output",
        "out.txt",
    ])
    err = capsys.readouterr().err
    assert rc == 0
    assert "timing record-vendor-task: WARNING: ledger write skipped" in err
    assert "blocked ledger" in err


def test_timing_telemetry_mark_writes_ledgers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    implement_tmpdir = Path("/tmp") / f"larch-telemetry-{tmp_path.name}"
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    timing_ledger = implement_tmpdir / "timing-ledger.tsv"
    _ = (implement_tmpdir / "session-env.sh").write_text(
        f"LARCH_TIMING_LEDGER={timing_ledger}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TMPDIR", "/tmp")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(implement_tmpdir))
    rc = timing.step_telemetry_mark(implement_tmpdir=implement_tmpdir, label="telemetry-fixture")
    assert rc == 0
    token_ledgers = list(implement_tmpdir.glob("larch-tokens-*.jsonl"))
    assert token_ledgers
    token_dump = token_ledgers[0].read_text(encoding="utf-8")
    timing_dump = timing_ledger.read_text(encoding="utf-8")
    assert "telemetry-fixture" in token_dump
    assert "telemetry-fixture" in timing_dump


def test_timing_report_main_terse_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text(
        "v1\tmark\t10\timplement\tStep 0\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    rc = timing.timing_report_main(["--terse", "--ledger", str(ledger)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Step 0:" in out
    assert "elapsed=" in out


def test_timing_report_full_without_marks(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text("", encoding="utf-8")
    rendered = timing.TimingReport(ledger).render(mode="full", fmt="markdown")
    assert rendered == "Timing report unavailable: no step marks in ledger"


def test_timing_dump_main_rejects_invalid_ledger(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fifo = tmp_path / "fifo.tsv"
    if hasattr(stat, "S_IFIFO"):
        os.mkfifo(fifo)
        rc = timing.timing_dump_main(["--ledger", str(fifo)])
        assert rc == 1
        assert "timing dump:" in capsys.readouterr().err


def test_validate_ledger_path_empty_tmpdir_uses_system_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TMPDIR", "")
    monkeypatch.chdir(tmp_path)
    resolved = timing.validate_ledger_path("ledger.tsv", env={"TMPDIR": ""})
    assert tmp_path not in resolved.parents
    assert resolved == Path("/tmp/ledger.tsv") or resolved == Path("/private/tmp/ledger.tsv")


def test_timing_lock_timeout_skips_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text("", encoding="utf-8")
    times = iter([0.0, 10.0])
    monkeypatch.setattr(timing.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(timing.time, "sleep", lambda _x=0.0: None)

    def _blocked_flock(*_: object, **__: object) -> None:
        raise BlockingIOError

    monkeypatch.setattr(fcntl_mod, "flock", _blocked_flock)
    timing.TimingLedger(ledger).mark("blocked")
    assert ledger.read_text(encoding="utf-8") == ""
