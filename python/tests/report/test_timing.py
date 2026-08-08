"""Tests for the timing library surface Python runtime modules still import.

The `timing` commands are Rust-owned since issue #8083; their coverage lives in
`crates/larch-core/src/report/timing.rs` and `crates/larch-cli/tests/timing.rs`.
"""

from __future__ import annotations

import fcntl as fcntl_mod
import os
import stat
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from larch.report import timing


def test_mark_returns_a_frozen_result_and_appends_one_row(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    env = {"TMPDIR": str(tmp_path), "IMPLEMENT_TMPDIR": str(tmp_path)}
    result = timing.mark(label="Step 0", ledger=str(ledger), env=env)
    assert result.marked is True
    assert result.ledger_path == ledger
    with pytest.raises(FrozenInstanceError):
        result.marked = False  # pyright: ignore[reportAttributeAccessIssue]  # frozen dataclass write is the assertion
    parts = ledger.read_text(encoding="utf-8").splitlines()[0].split("\t")
    assert parts[:2] == ["v1", "mark"]
    assert parts[3:5] == ["implement", "Step 0"]
    assert len(parts) == timing.TIMING_VENDOR_MIN_COLS


def test_mark_without_a_resolvable_ledger_reports_no_write(tmp_path: Path) -> None:
    result = timing.mark(label="Step 0", env={"TMPDIR": str(tmp_path)})
    assert result == timing.TimingMarkResult(ledger_path=None, marked=False)


def test_mark_if_latest_differs_skips_only_an_identical_latest_label(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    env = {"TMPDIR": str(tmp_path)}
    assert timing.mark(label="Step 5", ledger=str(ledger), env=env, if_latest_differs=True).marked
    assert not timing.mark(label="Step 5", ledger=str(ledger), env=env, if_latest_differs=True).marked
    assert timing.mark(label="Step 6", ledger=str(ledger), env=env, if_latest_differs=True).marked
    steps = [line.split("\t")[4] for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert steps == ["Step 5", "Step 6"]


def test_record_vendor_task_writes_the_basename_and_normalizes_status(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).record_vendor_task(
        vendor="claude",
        task_kind="claude-review",
        start_s=10,
        end_s=25,
        output=str(tmp_path / "nested" / "claude.log"),
        status="TIMEOUT",
    )
    parts = ledger.read_text(encoding="utf-8").splitlines()[0].split("\t")
    assert parts[5:7] == ["claude", "claude-review"]
    assert parts[7:10] == ["10", "25", "15"]
    assert parts[10] == "claude.log"
    assert parts[12] == "signal"


def test_record_vendor_task_rejects_an_unknown_vendor_and_malformed_kind(tmp_path: Path) -> None:
    ledger = timing.TimingLedger(tmp_path / "timing-ledger.tsv")
    with pytest.raises(ValueError, match="vendor must be codex, cursor, or claude"):
        ledger.record_vendor_task(vendor="gemini", task_kind="codex-review", start_s=0, end_s=1, output="o")
    with pytest.raises(ValueError, match="malformed task-kind"):
        ledger.record_vendor_task(vendor="codex", task_kind="Codex Review", start_s=0, end_s=1, output="o")
    with pytest.raises(ValueError, match="--status must be"):
        ledger.record_vendor_task(vendor="codex", task_kind="codex-review", start_s=0, end_s=1, output="o", status="weird")


def test_record_vendor_task_warns_on_an_unknown_task_kind(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).record_vendor_task(
        vendor="codex", task_kind="codex-not-registered", start_s=0, end_s=1, output="o"
    )
    assert "unknown task-kind: codex-not-registered" in capsys.readouterr().err


def test_record_vendor_task_clamps_a_reversed_window_to_unknown(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).record_vendor_task(
        vendor="codex", task_kind="codex-review", start_s=50, end_s=10, output="o"
    )
    parts = ledger.read_text(encoding="utf-8").splitlines()[0].split("\t")
    assert parts[9] == "0"
    assert parts[12] == "unknown"


def test_record_round_clamps_negative_duration_and_keeps_oos(tmp_path: Path) -> None:
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
    parts = ledger.read_text(encoding="utf-8").splitlines()[0].split("\t")
    assert parts[8] == "0"
    assert parts[11] == "4"


def test_record_round_writes_incrementing_attempt(tmp_path: Path) -> None:
    # Issue #5504: a stall recovery reruns the same round in one session; each rerun must
    # record a distinct 1-based attempt index in the reserved trailing column so the progress
    # report can split the Gantt per attempt instead of merging both windows into one span.
    ledger = tmp_path / "timing-ledger.tsv"
    led = timing.TimingLedger(ledger)
    led.record_round(skill="implement", step="Step 5 — code review", round_n=1, start_s=100, end_s=200, accepted=1, rejected=0)
    led.record_round(skill="implement", step="Step 5 — code review", round_n=1, start_s=300, end_s=400, accepted=2, rejected=1)
    led.record_round(skill="implement", step="Step 5 — code review", round_n=2, start_s=500, end_s=600, accepted=0, rejected=0)
    rounds = [line.split("\t") for line in ledger.read_text(encoding="utf-8").splitlines() if "\tround\t" in line]
    assert [parts[5] for parts in rounds] == ["1", "1", "2"]
    assert [parts[12] for parts in rounds] == ["1", "2", "1"]
    assert all(len(parts) == 13 for parts in rounds)


def test_record_round_rejects_an_unknown_skill(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--skill must be implement or design"):
        timing.TimingLedger(tmp_path / "timing-ledger.tsv").record_round(
            skill="review", step="s", round_n=1, start_s=0, end_s=1, accepted=0, rejected=0
        )


def test_ledger_rejects_a_symlink_or_non_regular_target(tmp_path: Path) -> None:
    target = tmp_path / "target.tsv"
    _ = target.write_text("", encoding="utf-8")
    link = tmp_path / "link.tsv"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        timing.TimingLedger(link).mark("bad")
    fifo = tmp_path / "fifo"
    if hasattr(stat, "S_IFIFO"):
        os.mkfifo(fifo)
        with pytest.raises(ValueError, match="not a regular file"):
            timing.TimingLedger(fifo).mark("bad")


def test_ledger_rows_sanitize_embedded_separators(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).mark("Step\t1\nnext")
    assert ledger.read_text(encoding="utf-8").splitlines() == [
        "\t".join(["v1", "mark", ledger.read_text(encoding="utf-8").split("\t")[2], "implement", "Step<NUL>1<NUL>next", *(["-"] * 8)])
    ]


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


def test_validate_ledger_path_rejects_empty_and_parent_traversal(tmp_path: Path) -> None:
    env = {"TMPDIR": str(tmp_path)}
    with pytest.raises(ValueError, match="must not be empty or contain"):
        _ = timing.validate_ledger_path("", env=env)
    with pytest.raises(ValueError, match="must not be empty or contain"):
        _ = timing.validate_ledger_path(str(tmp_path / ".." / "x.tsv"), env=env)


def test_validate_ledger_path_empty_tmpdir_uses_system_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TMPDIR", "")
    monkeypatch.chdir(tmp_path)
    resolved = timing.validate_ledger_path("ledger.tsv", env={"TMPDIR": ""})
    assert tmp_path not in resolved.parents
    assert resolved == Path("/tmp/ledger.tsv") or resolved == Path("/private/tmp/ledger.tsv")


def test_resolve_timing_ledger_path_prefers_tmpdir_keys_in_order(tmp_path: Path) -> None:
    implement = tmp_path / "implement"
    design = tmp_path / "design"
    implement.mkdir()
    design.mkdir()
    env = {"TMPDIR": str(tmp_path), "IMPLEMENT_TMPDIR": str(implement), "DESIGN_TMPDIR": str(design)}
    assert timing.resolve_timing_ledger_path(env=env) == implement.resolve() / "timing-ledger.tsv"
    assert timing.resolve_timing_ledger_path(env={k: v for k, v in env.items() if k != "IMPLEMENT_TMPDIR"}) == (
        design.resolve() / "timing-ledger.tsv"
    )
    assert timing.resolve_timing_ledger_path(env={"TMPDIR": str(tmp_path)}) is None


def test_resolve_timing_ledger_path_ignores_an_unusable_env_ledger(tmp_path: Path) -> None:
    implement = tmp_path / "implement"
    implement.mkdir()
    env = {
        "TMPDIR": str(tmp_path),
        "IMPLEMENT_TMPDIR": str(implement),
        "LARCH_TIMING_LEDGER": "/etc/timing-ledger.tsv",
    }
    assert timing.resolve_timing_ledger_path(env=env) == implement.resolve() / "timing-ledger.tsv"


def test_lock_timeout_skips_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
