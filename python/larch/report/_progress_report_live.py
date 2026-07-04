"""Live run discovery, timing helpers, and terminal rendering for progress_report."""
# ruff: noqa: F401
# pylint: skip-file
# pyright: reportUnknownVariableType=false, reportUnusedCallResult=false, reportUnusedImport=false, reportUnusedFunction=false, reportUnusedClass=false

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import json
import os
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from larch.agents import collect_results
from larch.core import env_file
from larch.rendering.gantt import GanttRow, format_mss, render_gantt
from larch import io as larch_io
from larch.core import config
from larch.core import logging_util
from larch.review import plan_review_round
from larch.report import report_tokens_cost
from larch.review import voting


TIMING_MARK_MIN_COLS = 5
TIMING_V1_MIN_COLS = 3
TIMING_LEGACY_DESIGN_ROUND_MIN_COLS = 4
TIMING_LEGACY_DESIGN_ROUND_START_COL = 0
TIMING_LEGACY_DESIGN_ROUND_END_COL = 1
TIMING_LEGACY_DESIGN_ROUND_SKILL_COL = 2
TIMING_LEGACY_DESIGN_ROUND_KIND_COL = 3
TIMING_ROUND_MIN_COLS = 8
TIMING_ROUND_SKILL_COL = 3
TIMING_ROUND_ROUND_NUM_COL = 5
TIMING_ROUND_END_COL = 7
# Issue #5504: reserved trailing column repurposed as the 1-based round attempt index
# (written by timing.TimingLedger.record_round). Rows predating it carry "-" -> attempt 1.
TIMING_ROUND_ATTEMPT_COL = 12
TIMING_VENDOR_MIN_COLS = 13
TIMING_VENDOR_VENDOR_COL = 5
TIMING_VENDOR_KIND_COL = 6
TIMING_VENDOR_START_COL = 7
TIMING_VENDOR_END_COL = 8
TIMING_VENDOR_OUTPUT_COL = 10
TIMING_VENDOR_STATUS_COL = 12
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
RENDER_PHASE_DETAIL_TIMEOUT_SECONDS = 15
PROGRESS_GANTT_ROW_CAP = 25
MIN_MARKDOWN_TABLE_PARTS = 4
MIN_TSV_RESULT_COLS = 3
LABEL_MAP_MIN_COLS = 2
MD_RESULT_COL_FROM_END = 2
MD_FALLBACK_RESULT_COL_FROM_END = 3

_MD_TABLE_SEP_RE = re.compile(r"^\|[ :\-|]+\|$")
_MD_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<![_\w])_([^_\n]+)_(?![_\w])")
_MD_HEADING_RE = re.compile(r"^#{1,6} ")



def _strip_md_for_terminal(text: str) -> str:
    """Remove Markdown decorators for plain-text terminal display."""
    lines: list[str] = []
    for raw in text.splitlines():
        if _MD_TABLE_SEP_RE.match(raw.strip()):
            continue
        out = _MD_HEADING_RE.sub("", raw, count=1)
        out = _MD_BOLD_RE.sub(r"\1", out)
        out = _MD_ITALIC_RE.sub(r"\1", out)
        lines.append(out)
    return "\n".join(lines)


@dataclass(frozen=True)
class LiveRun:
    skill: str
    tmpdir: Path
    cwd: str
    pointer: Path
    mtime: float


def _sessions_root() -> Path:
    return Path.home() / ".cache" / "larch" / "sessions"


def _canonical_repo_path(path: str) -> str:
    if not path:
        return ""
    try:
        return os.path.realpath(path)
    except OSError:
        return path


def _read_env_file(path: Path) -> dict[str, str]:
    return env_file.read_env_file(path)


def _kv_value(*, path: Path, key: str) -> str:
    return _read_env_file(path).get(key, "")


def _path_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _latest_timing_ledger_activity_ts(ledger: Path) -> int | None:
    """Latest epoch across mark, vendor, and round rows in a timing ledger."""
    latest_ts: int | None = None
    try:
        lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return latest_ts
    for line in lines:
        cols = line.split("\t")
        candidates: list[str]
        if len(cols) >= TIMING_V1_MIN_COLS and cols[0] == "v1":
            row_kind = cols[1]
            if row_kind == "mark":
                candidates = [cols[2]]
            elif row_kind == "vendor" and len(cols) > TIMING_VENDOR_END_COL:
                candidates = [cols[2], cols[TIMING_VENDOR_END_COL]]
            elif row_kind == "round" and len(cols) > TIMING_ROUND_END_COL:
                candidates = [cols[2], cols[TIMING_ROUND_END_COL]]
            else:
                continue
        elif (
            len(cols) >= TIMING_LEGACY_DESIGN_ROUND_MIN_COLS
            and cols[TIMING_LEGACY_DESIGN_ROUND_SKILL_COL] == "design"
            and cols[TIMING_LEGACY_DESIGN_ROUND_KIND_COL] == "round"
        ):
            candidates = [
                cols[TIMING_LEGACY_DESIGN_ROUND_START_COL],
                cols[TIMING_LEGACY_DESIGN_ROUND_END_COL],
            ]
        else:
            continue
        for raw in candidates:
            try:
                ts = int(raw)
            except ValueError:
                continue
            if latest_ts is None or ts > latest_ts:
                latest_ts = ts
    return latest_ts


def _run_activity_mtime(*, timing_ledger: Path, pointer: Path) -> float:
    """Liveness signal for ranking concurrent runs in the same repo.

    The implement pointer file is written once at Step 0 and never refreshed, so a
    long-running session (e.g. mid Step 5 review) keeps a Step-0-frozen pointer mtime and
    loses discovery to a stale run whose pointer was created later (issue #4954). The
    tmpdir-root mtime has the opposite failure: a spurious write to the root dir of a stale
    run hides the active session (issue #4661, which switched root mtime to pointer mtime).
    Step 5 emits one mark at entry while vendor and round ledger rows advance during
    multi-round review, so ranking uses the latest timestamp across all three row kinds.
    Fall back to the pointer mtime only before the first ledger row is written.
    """
    latest_ts = _latest_timing_ledger_activity_ts(timing_ledger)
    if latest_ts is not None:
        return float(latest_ts)
    return _path_mtime(pointer)


def _design_candidate(pointer: Path) -> LiveRun | None:
    if not pointer.is_symlink():
        return None
    try:
        target = pointer.resolve(strict=True)
    except OSError:
        return None
    values = _read_env_file(target)
    tmpdir_s = values.get("DESIGN_TMPDIR") or values.get("SESSION_TMPDIR") or ""
    if not tmpdir_s:
        return None
    tmpdir = Path(tmpdir_s)
    if not tmpdir.is_dir():
        return None
    cwd = _kv_value(path=tmpdir / ".larch-keepalive", key="CLONE_PATH")
    if not cwd:
        return None
    return LiveRun("design", tmpdir, cwd, pointer, _run_activity_mtime(timing_ledger=tmpdir / "timing-ledger.tsv", pointer=pointer))


def _implement_candidate(pointer: Path) -> LiveRun | None:
    if pointer.is_symlink() or not pointer.is_file():
        return None
    values = _read_env_file(pointer)
    tmpdir_s = values.get("IMPLEMENT_TMPDIR", "")
    cwd = values.get("REPO_CWD", "")
    if not tmpdir_s or not cwd:
        return None
    tmpdir = Path(tmpdir_s)
    if not tmpdir.is_dir():
        return None
    return LiveRun(
        "implement", tmpdir, cwd, pointer, _run_activity_mtime(timing_ledger=tmpdir / "timing-ledger.tsv", pointer=pointer)
    )


def _discover_live_run(cwd: str) -> LiveRun | None:
    if not cwd.strip():
        return None
    canonical_cwd = _canonical_repo_path(cwd)
    root = _sessions_root()
    try:
        pointers = list(root.glob("current-implement-env-*.sh")) + list(
            root.glob("current-design-env-*.sh")
        )
    except OSError:
        return None
    candidates: list[LiveRun] = []
    for pointer in pointers:
        if pointer.name.startswith("current-implement-env-"):
            candidate = _implement_candidate(pointer)
        else:
            candidate = _design_candidate(pointer)
        if candidate is None:
            continue
        if _canonical_repo_path(candidate.cwd) != canonical_cwd:
            continue
        candidates.append(candidate)
    if not candidates:
        return None
    return max(candidates, key=lambda run: run.mtime)


def _latest_timing_mark(ledger: Path) -> tuple[str, int | None]:
    latest_ts: int | None = None
    latest_label = ""
    try:
        lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return latest_label, latest_ts
    for line in lines:
        cols = line.split("\t")
        if len(cols) < TIMING_MARK_MIN_COLS or cols[0] != "v1" or cols[1] != "mark":
            continue
        try:
            ts = int(cols[2])
        except ValueError:
            continue
        if latest_ts is None or ts >= latest_ts:
            latest_ts = ts
            latest_label = cols[4]
    return latest_label, latest_ts


def _latest_timing_mark_for_label(*, ledger: Path, label_matcher: Callable[[str], bool]) -> int | None:
    latest_ts: int | None = None
    try:
        lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return latest_ts
    for line in lines:
        cols = line.split("\t")
        if len(cols) < TIMING_MARK_MIN_COLS or cols[0] != "v1" or cols[1] != "mark":
            continue
        try:
            ts = int(cols[2])
        except ValueError:
            continue
        if not label_matcher(cols[4]):
            continue
        if latest_ts is None or ts >= latest_ts:
            latest_ts = ts
    return latest_ts


def _human_elapsed(start_s: int | None, *, now: int | None = None) -> str:
    if start_s is None:
        return "unknown"
    current = int(time.time()) if now is None else now
    elapsed = max(0, current - start_s)
    if elapsed >= SECONDS_PER_HOUR:
        hours = elapsed // SECONDS_PER_HOUR
        minutes = (elapsed % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
        return f"{hours}h {minutes}m"
    if elapsed >= SECONDS_PER_MINUTE:
        return f"{elapsed // SECONDS_PER_MINUTE}m"
    return f"{elapsed}s"


def _last_artifact(tmpdir: Path) -> str:
    newest_path: Path | None = None
    newest_mtime = 0.0
    for root, dirs, files in os.walk(tmpdir):
        dirs[:] = [name for name in dirs if name != ".git"]
        for name in files:
            candidate = Path(root) / name
            try:
                stat = candidate.stat()
            except OSError:
                continue
            if stat.st_mtime >= newest_mtime:
                newest_mtime = stat.st_mtime
                newest_path = candidate
    if newest_path is None:
        return "last artifact: none"
    stamp = datetime.fromtimestamp(newest_mtime, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
    try:
        shown = newest_path.relative_to(tmpdir)
    except ValueError:
        shown = newest_path
    return f"last artifact: {stamp} {shown}"


def _render_generic(*, skill: str, step_label: str, start_s: int | None, tmpdir: Path) -> str:
    label = step_label or "unknown step"
    return f"{skill}: {label}: started {_human_elapsed(start_s)} ago\n{_last_artifact(tmpdir)}"


def _render_ship_pr(implement_tmpdir: Path) -> str:
    state = _read_env_file(implement_tmpdir / "ship-pr-state.sh")
    phase = state.get("PHASE", "") or "unknown"
    lines = [f"Ship-PR phase: {phase}"]
    pr_number = state.get("PR_NUMBER", "")
    pr_url = state.get("PR_URL", "")
    if pr_number or pr_url:
        pr_label = f"#{pr_number}" if pr_number else ""
        lines.append(f"PR: {pr_label} {pr_url}".rstrip())
    iteration = state.get("ITERATION", "")
    if iteration:
        lines.append(f"iteration: {iteration}")
    ci_passed = state.get("CI_PASSED", "")
    if ci_passed:
        lines.append(f"CI passed: {ci_passed}")
    failed_run_id = state.get("FAILED_RUN_ID", "")
    if failed_run_id:
        lines.append(f"failed run: {failed_run_id}")
    stall_step = state.get("STALL_STEP", "")
    if stall_step:
        lines.append(f"stall step: {stall_step}")
    bail_reason = state.get("BAIL_REASON", "")
    if bail_reason:
        lines.append(f"bail reason: {bail_reason}")
    merge_result = state.get("MERGE_RESULT", "")
    if merge_result:
        lines.append(f"merge result: {merge_result}")
    return "\n".join(lines)


def _round_number(path: Path) -> int | None:
    match = re.match(r"^round-([1-9][0-9]*)$", path.name)
    if not match:
        return None
    return int(match.group(1))


def _round_dirs(implement_tmpdir: Path) -> list[Path]:
    try:
        dirs = [p for p in implement_tmpdir.iterdir() if p.is_dir() and _round_number(p) is not None]
    except OSError:
        return []
    return sorted(dirs, key=lambda p: _round_number(p) or 0)


def _all_round_dirs_inflight(rounds_root: Path) -> bool:
    dirs = _round_dirs(rounds_root)
    if not dirs:
        return False
    for round_dir in dirs:
        meta_path = round_dir / "round-meta.json"
        try:
            _ = meta_path.lstat()
            return False
        except FileNotFoundError:
            continue
        except OSError:
            return False
    return True


def _current_round_dir(rounds_root: Path) -> Path | None:
    dirs = _round_dirs(rounds_root)
    if not dirs:
        return None
    unsettled = [path for path in dirs if not (path / "review-and-fix.env").exists()]
    return unsettled[-1] if unsettled else dirs[-1]


def _count_lines(path: Path) -> int:
    try:
        return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line)
    except OSError:
        return 0


def _returned_reviewers(round_dir: Path) -> int:
    collector = round_dir / "collector-results.env"
    if collector.is_file():
        try:
            return sum(
                1
                for line in collector.read_text(encoding="utf-8", errors="replace").splitlines()
                if "STATUS=OK" in line
            )
        except OSError:
            return 0
    count = 0
    try:
        for path in round_dir.glob("*-output.txt"):
            if path.is_file() and path.stat().st_size > 0:
                count += 1
    except OSError:
        return 0
    return count


def _round_elapsed(round_dir: Path) -> str:
    try:
        start_s = int((round_dir / "round-start-s").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return "unknown"
    elapsed = max(0, int(time.time()) - start_s)
    return f"{elapsed // SECONDS_PER_MINUTE}m"


def _resolve_run_id(implement_tmpdir: Path) -> str:
    for path in (implement_tmpdir / "session-env.sh", implement_tmpdir / "parent-issue.md"):
        run_id = _kv_value(path=path, key="LARCH_RUN_ID") or _kv_value(path=path, key="RUN_ID")
        if run_id:
            return run_id
    try:
        manifests = list((implement_tmpdir / "larch-logs" / "implement").glob("*/manifest.json"))
    except OSError:
        manifests = []
    if len(manifests) == 1:
        return manifests[0].parent.name
    try:
        return (implement_tmpdir / "session-id").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _review_rounds_root(*, implement_tmpdir: Path, run_id: str) -> Path:
    run_log_root: Path | None = implement_tmpdir / "larch-logs" / "implement" / run_id if run_id else None
    if run_log_root is not None and run_log_root.is_dir() and _round_dirs(run_log_root):
        return run_log_root
    return implement_tmpdir


def _has_completed_round_meta(rounds_root: Path) -> bool:
    return any((round_dir / "round-meta.json").is_file() for round_dir in _round_dirs(rounds_root))


def _latest_token_ledger(tmpdir: Path) -> Path | None:
    try:
        token_ledgers: list[Path] = sorted(tmpdir.glob("larch-tokens-*.jsonl"), key=_path_mtime)
    except OSError:
        return None
    return token_ledgers[-1] if token_ledgers else None


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict):
        return cast("dict[str, object]", parsed)
    return {}


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _nested_dict(*, data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return {}


def _add_round_vendor_cost_row(
    *,
    data: dict[str, object],
    sums: dict[str, dict[str, int]],
    claude_sub_by_model: dict[str, dict[str, int]],
) -> None:
    vendor = str(data.get("vendor") or "")
    if vendor not in {"codex", "cursor", "claude_sub"}:
        return
    model = str(data.get("model") or "")
    if vendor == "claude_sub":
        model = model or config.claude_sub_default_model(str(data.get("raw") or ""))
        bucket = claude_sub_by_model.setdefault(model, {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0})
        bucket["input"] += _as_int(data.get("input"))
        bucket["cache_read"] += _as_int(data.get("cache_read"))
        bucket["cache_create_5m"] += _as_int(data.get("cache_create"))
        bucket["output"] += _as_int(data.get("output"))
        return
    bucket_key = "codex_mini" if vendor == "codex" and model == report_tokens_cost.CODEX_MINI_MODEL else vendor
    bucket = sums.setdefault(bucket_key, {"input": 0, "cache_read": 0, "cache_create": 0, "output": 0})
    bucket["input"] += _as_int(data.get("input"))
    bucket["cache_read"] += _as_int(data.get("cache_read"))
    bucket["cache_create"] += _as_int(data.get("cache_create"))
    bucket["output"] += _as_int(data.get("output"))


def _round_vendor_cost_argv(
    *,
    sums: dict[str, dict[str, int]],
    claude_sub_by_model: dict[str, dict[str, int]],
) -> list[str]:
    argv: list[str] = []
    for vendor, bucket in sums.items():
        if vendor == "codex":
            argv.extend(["--codex-input-tokens", str(bucket["input"]), "--codex-cached-input-tokens", str(bucket["cache_read"]), "--codex-output-tokens", str(bucket["output"])])
        elif vendor == "codex_mini":
            argv.extend(["--codex-mini-input-tokens", str(bucket["input"]), "--codex-mini-cached-input-tokens", str(bucket["cache_read"]), "--codex-mini-output-tokens", str(bucket["output"])])
        elif vendor == "cursor":
            argv.extend(["--cursor-input-tokens", str(bucket["input"]), "--cursor-cache-read-tokens", str(bucket["cache_read"]), "--cursor-output-tokens", str(bucket["output"])])
    if claude_sub_by_model:
        argv.extend(report_tokens_cost.claude_sub_argv_from_buckets(by_model=claude_sub_by_model, bucket={}))
    return argv


def _fmt_hms(seconds: int | None) -> str:
    if seconds is None or seconds <= 0:
        return "N/A"
    hours = seconds // SECONDS_PER_HOUR
    minutes = (seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
    secs = seconds % SECONDS_PER_MINUTE
    if hours > 0:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes > 0:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _read_lines_best_effort(path: Path | None) -> list[str]:
    if path is None:
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _timing_round_windows(
    timing_ledger: Path | None,
    *,
    skill: str,
    round_num: int,
    skill_filtered: bool,
) -> tuple[int, int] | None:
    starts: list[int] = []
    ends: list[int] = []
    round_s = str(round_num)
    for line in _read_lines_best_effort(timing_ledger):
        cols = line.split("\t")
        if len(cols) < TIMING_ROUND_MIN_COLS or cols[0] != "v1" or cols[1] != "round":
            continue
        if skill_filtered and cols[TIMING_ROUND_SKILL_COL] != skill:
            continue
        if cols[TIMING_ROUND_ROUND_NUM_COL] != round_s:
            continue
        try:
            starts.append(int(cols[6]))
            ends.append(int(cols[TIMING_ROUND_END_COL]))
        except ValueError:
            continue
    if not starts or not ends:
        return None
    return min(starts), max(ends)


def _timing_round_attempt_windows(
    timing_ledger: Path | None,
    *,
    round_num: int,
    skill_filtered: bool = False,
    skill: str = "",
) -> list[tuple[int, int, int]]:
    """Per-attempt ``(attempt, start, end)`` windows for a round number, ordered by attempt.

    Issue #5504: a stall recovery can rerun the same round in one session, writing multiple
    ``v1 round`` rows for the same round number. Grouping by the explicit attempt column
    (``TIMING_ROUND_ATTEMPT_COL``) keeps each attempt's reviewer and post-aggregation probe
    rows inside their own window instead of collapsing them into one merged span. Rows that
    predate the attempt column (trailing ``-``) default to attempt 1, so legacy ledgers render
    exactly as before.
    """
    by_attempt: dict[int, tuple[int, int]] = {}
    round_s = str(round_num)
    for line in _read_lines_best_effort(timing_ledger):
        cols = line.split("\t")
        if len(cols) < TIMING_ROUND_MIN_COLS or cols[0] != "v1" or cols[1] != "round":
            continue
        if skill_filtered and cols[TIMING_ROUND_SKILL_COL] != skill:
            continue
        if cols[TIMING_ROUND_ROUND_NUM_COL] != round_s:
            continue
        try:
            start_s = int(cols[6])
            end_s = int(cols[TIMING_ROUND_END_COL])
        except ValueError:
            continue
        attempt = 1
        if len(cols) > TIMING_ROUND_ATTEMPT_COL and cols[TIMING_ROUND_ATTEMPT_COL].isdigit():
            attempt = int(cols[TIMING_ROUND_ATTEMPT_COL])
        if attempt in by_attempt:
            prev_start, prev_end = by_attempt[attempt]
            by_attempt[attempt] = (min(prev_start, start_s), max(prev_end, end_s))
        else:
            by_attempt[attempt] = (start_s, end_s)
    return [(attempt, window[0], window[1]) for attempt, window in sorted(by_attempt.items())]


def _round_vendor_cost(*, token_ledger: Path | None, start_s: int | None, end_s: int | None) -> str:
    if token_ledger is None or not token_ledger.is_file() or start_s is None or end_s is None:
        return "N/A"
    sums: dict[str, dict[str, int]] = {}
    claude_sub_by_model: dict[str, dict[str, int]] = {}
    for line in _read_lines_best_effort(token_ledger):
        if not line.strip():
            continue
        try:
            row: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        data = cast("dict[str, object]", row)
        if data.get("type") != "vendor":
            continue
        ts_raw = data.get("ts")
        if not isinstance(ts_raw, str):
            continue
        try:
            ts = int(datetime.fromisoformat(ts_raw).timestamp())
        except ValueError:
            continue
        if ts < start_s or ts > end_s:
            continue
        _add_round_vendor_cost_row(data=data, sums=sums, claude_sub_by_model=claude_sub_by_model)
    if not sums and not claude_sub_by_model:
        return "$0.00"
    argv = _round_vendor_cost_argv(sums=sums, claude_sub_by_model=claude_sub_by_model)
    try:
        out = report_tokens_cost.token_cost_from_args(argv)
    except Exception:  # pylint: disable=broad-except
        return "N/A"
    for line in out.splitlines():
        key, sep, value = line.partition("=")
        if sep and key == "TOTAL_COST" and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            return f"${value}"
    return "N/A"


@dataclass(frozen=True)
class _PhaseRound:
    number: int
    suggestions: int
    accepted: int
    oos_proposed: int
    oos_accepted: int
    reviewers: int
    seconds: int | None
    cost: str
    gantt_window: tuple[int, int] | None
    # Issue #4882: canonical scope-aware decomposition (None when round-meta predates the field or
    # has no classification data, e.g. design plan-review rounds).
    inscope: int | None = None
    oos_total: int | None = None
    nit_pruned: int = 0
