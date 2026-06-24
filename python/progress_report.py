"""On-demand progress reports for live larch runs."""
# pyright: reportUnknownVariableType=false, reportUnusedCallResult=false

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import collect_results
import env_file
from gantt import GanttRow, format_mss, render_gantt
import larch_io
import logging_util
import plan_review_round
import report_tokens_cost
import voting

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


def _kv_value(path: Path, key: str) -> str:
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


def _run_activity_mtime(timing_ledger: Path, pointer: Path) -> float:
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
    cwd = _kv_value(tmpdir / ".larch-keepalive", "CLONE_PATH")
    if not cwd:
        return None
    return LiveRun("design", tmpdir, cwd, pointer, _run_activity_mtime(tmpdir / "timing-ledger.tsv", pointer))


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
        "implement", tmpdir, cwd, pointer, _run_activity_mtime(tmpdir / "timing-ledger.tsv", pointer)
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


def _latest_timing_mark_for_label(ledger: Path, label_matcher: Callable[[str], bool]) -> int | None:
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


def _render_generic(skill: str, step_label: str, start_s: int | None, tmpdir: Path) -> str:
    label = step_label or "unknown step"
    return f"{skill}: {label} — started {_human_elapsed(start_s)} ago\n{_last_artifact(tmpdir)}"


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
        run_id = _kv_value(path, "LARCH_RUN_ID") or _kv_value(path, "RUN_ID")
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


def _review_rounds_root(implement_tmpdir: Path, run_id: str) -> Path:
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


def _nested_dict(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return {}


def _fmt_hms(seconds: int | None) -> str:
    if seconds is None or seconds <= 0:
        return "—"
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


def _round_vendor_cost(token_ledger: Path | None, start_s: int | None, end_s: int | None) -> str:
    if token_ledger is None or not token_ledger.is_file() or start_s is None or end_s is None:
        return "—"
    sums: dict[str, dict[str, int]] = {}
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
        vendor = str(data.get("vendor") or "")
        if vendor not in {"codex", "cursor", "claude_sub"}:
            continue
        bucket = sums.setdefault(vendor, {"input": 0, "cache_read": 0, "cache_create": 0, "output": 0})
        bucket["input"] += _as_int(data.get("input"))
        bucket["cache_read"] += _as_int(data.get("cache_read"))
        bucket["cache_create"] += _as_int(data.get("cache_create"))
        bucket["output"] += _as_int(data.get("output"))
    if not sums:
        return "$0.00"
    argv: list[str] = []
    for vendor, bucket in sums.items():
        if vendor == "codex":
            argv.extend([
                "--codex-input-tokens",
                str(bucket["input"]),
                "--codex-cached-input-tokens",
                str(bucket["cache_read"]),
                "--codex-output-tokens",
                str(bucket["output"]),
            ])
        elif vendor == "cursor":
            argv.extend([
                "--cursor-input-tokens",
                str(bucket["input"]),
                "--cursor-cache-read-tokens",
                str(bucket["cache_read"]),
                "--cursor-output-tokens",
                str(bucket["output"]),
            ])
        elif vendor == "claude_sub":
            argv.extend([
                "--claude-sub-input-tokens",
                str(bucket["input"]),
                "--claude-sub-cache-read-tokens",
                str(bucket["cache_read"]),
                "--claude-sub-cache-write-5m-tokens",
                str(bucket["cache_create"]),
                "--claude-sub-output-tokens",
                str(bucket["output"]),
            ])
    try:
        out = report_tokens_cost.token_cost_from_args(argv)
    except Exception:  # pylint: disable=broad-except
        return "—"
    for line in out.splitlines():
        key, sep, value = line.partition("=")
        if sep and key == "TOTAL_COST" and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            return f"${value}"
    return "—"


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


def _completed_round_dirs(rounds_root: Path) -> list[Path]:
    if not rounds_root.is_dir() or not os.access(rounds_root, os.R_OK | os.X_OK):
        return []
    try:
        candidates = [p for p in rounds_root.iterdir() if p.is_dir() and (p / "round-meta.json").is_file()]
    except OSError:
        return []
    return sorted([p for p in candidates if _round_number(p) is not None], key=lambda p: _round_number(p) or 0)


def _phase_round_from_meta(
    round_dir: Path,
    *,
    skill: str,
    timing_ledger: Path | None,
    token_ledger: Path | None,
) -> _PhaseRound:
    meta = _read_json_object(round_dir / "round-meta.json")
    tally = _nested_dict(meta, "tally")
    summary = _nested_dict(meta, "summary")
    counts = _nested_dict(summary, "finding_counts")
    panel = _nested_dict(summary, "panel")
    accepted = _as_int(tally.get("ACCEPTED_COUNT", counts.get("total_accepted")))
    rejected = _as_int(tally.get("REJECTED_COUNT", counts.get("total_rejected")))
    exonerated = _as_int(tally.get("EXONERATED_COUNT", counts.get("total_exonerated")))
    neutral = _as_int(tally.get("NEUTRAL_COUNT", counts.get("total_neutral")))
    oos_accepted = _as_int(tally.get("OOS_ACCEPTED_COUNT"))
    oos_rejected = _as_int(tally.get("OOS_REJECTED_COUNT"))
    reviewers = _as_int(panel.get("total_slot_count"))
    if reviewers == 0:
        reviewers = _as_int(panel.get("static_slot_count")) + _as_int(panel.get("dynamic_slot_count"))
    round_num = _round_number(round_dir) or 0
    table_window = _timing_round_windows(timing_ledger, skill=skill, round_num=round_num, skill_filtered=True)
    gantt_window = _timing_round_windows(timing_ledger, skill=skill, round_num=round_num, skill_filtered=False)
    seconds = None
    if table_window is not None and table_window[1] > table_window[0]:
        seconds = table_window[1] - table_window[0]
    cost = _round_vendor_cost(
        token_ledger,
        table_window[0] if table_window else None,
        table_window[1] if table_window else None,
    )
    canonical = _nested_dict(meta, "tally_canonical")
    inscope: int | None = None
    oos_total: int | None = None
    if canonical:
        inscope = (
            _as_int(canonical.get("ACCEPTED_COUNT"))
            + _as_int(canonical.get("REJECTED_COUNT"))
            + _as_int(canonical.get("NEUTRAL_COUNT"))
            + _as_int(canonical.get("EXONERATED_COUNT"))
        )
        oos_total = _as_int(canonical.get("OOS_ACCEPTED_COUNT")) + _as_int(canonical.get("OOS_REJECTED_COUNT"))
    return _PhaseRound(
        number=round_num,
        suggestions=accepted + rejected + exonerated + neutral,
        accepted=accepted,
        oos_proposed=oos_accepted + oos_rejected,
        oos_accepted=oos_accepted,
        reviewers=reviewers,
        seconds=seconds,
        cost=cost,
        gantt_window=gantt_window if gantt_window is not None and gantt_window[1] > gantt_window[0] else None,
        inscope=inscope,
        oos_total=oos_total,
        nit_pruned=_as_int(meta.get("nit_pruned_count")),
    )


def _accepted_reviewer_basenames(findings_file: Path | None) -> list[str]:
    names: list[str] = []
    for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(findings_file)):
        if row.get("outcome") != "accepted":
            continue
        slots = row.get("reviewer_slots")
        if isinstance(slots, list):
            names.extend(Path(item).name for item in slots if isinstance(item, str) and item)
        else:
            reviewer = row.get("reviewer")
            if isinstance(reviewer, str) and reviewer:
                names.append(Path(reviewer).name)
    return names


def _top_reviewers(
    findings_file: Path | None,
    *,
    label_map: dict[str, str],
    top_n: int,
) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for basename in _accepted_reviewer_basenames(findings_file):
        label = label_map.get(basename) or _progress_derived_label(basename)
        counts[label] = counts.get(label, 0) + 1
    return list(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n])


def _classification_tsv_available(round_dirs: list[Path]) -> bool:
    return any(_tsv_has_data_rows(round_dir / "findings-classification.tsv") for round_dir in round_dirs)


def _human_attribution_labels(round_dirs: list[Path], *, reviewer_column: str) -> list[str]:
    if reviewer_column != "finding_reviewers":
        return []
    labels: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        clean = label.strip()
        if clean and clean not in seen:
            labels.append(clean)
            seen.add(clean)

    for round_dir in round_dirs:
        for label_map in (
            round_dir / "plan-review-prune-label-map.tsv",
            round_dir.parent.parent / "plan-review-prune-label-map.tsv",
        ):
            if not label_map.is_file():
                continue
            for line in _read_lines_best_effort(label_map):
                parts = line.split("\t")
                if len(parts) >= LABEL_MAP_MIN_COLS:
                    add(parts[1])
        for manifest in (round_dir / "panel-manifest.ndjson", round_dir / "plan-review-slots.ndjson"):
            for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(manifest)):
                slot = row.get("slot")
                if isinstance(slot, str):
                    add(plan_review_round._slot_human_label(slot))  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        lines = _read_lines_best_effort(round_dir / "findings-classification.tsv")
        if not lines:
            continue
        header = [col.strip() for col in lines[0].split("\t")]
        if reviewer_column not in header:
            continue
        reviewer_idx = header.index(reviewer_column)
        for line in lines[1:]:
            cols = line.split("\t")
            if len(cols) <= reviewer_idx:
                continue
            voting.grow_attribution_labels(labels, seen, cols[reviewer_idx])
    return labels


def _classification_row_in_scope(cols: dict[str, str], header: list[str]) -> bool:
    if "scope" in header:
        return cols.get("scope", "").strip() == "in_scope"
    return not cols.get("finding_id", "").strip().startswith("OOS_")


def _accepted_reviewers_from_classification(
    classification: Path,
    *,
    round_dirs: list[Path],
    label_map: dict[str, str] | None = None,
    active_bonus: float = 0.0,
) -> list[tuple[str, float]]:
    """Weighted in-scope accepted-finding reviewer attribution from classification TSV."""
    lines = _read_lines_best_effort(classification)
    if not lines:
        return []
    header = [col.strip() for col in lines[0].split("\t")]
    reviewer_column = "finding_reviewers" if "finding_reviewers" in header else "reviewer_slots" if "reviewer_slots" in header else ""
    if not reviewer_column or "voting_result" not in header:
        return []
    labels = _human_attribution_labels(round_dirs, reviewer_column=reviewer_column)
    rows: list[tuple[str, float]] = []
    for line in lines[1:]:
        raw_cols = line.split("\t")
        cols = {name: raw_cols[idx].strip() if idx < len(raw_cols) else "" for idx, name in enumerate(header)}
        if cols.get("voting_result") != "accepted" or not _classification_row_in_scope(cols, header):
            continue
        reviewer_cell = cols.get(reviewer_column, "")
        raw_reviewers = voting.raw_sole_finder_attribution(
            reviewer_cell,
            column=reviewer_column,
            corpus_labels=labels,
        )
        reviewers = voting.split_classification_attribution(
            reviewer_cell,
            column=reviewer_column,
            labels=labels if reviewer_column == "finding_reviewers" else None,
        )
        if not reviewers and reviewer_column == "finding_reviewers":
            cell = reviewer_cell.strip()
            if cell:
                reviewers = [part.strip() for part in cell.split(",") if part.strip()]
        points = float(voting.accepted_points_from_classification_row(cols, header))
        if active_bonus > 0 and len(raw_reviewers) == 1:
            points += active_bonus
        for reviewer in reviewers:
            label = reviewer
            if reviewer_column == "reviewer_slots":
                maps = label_map or {}
                label = maps.get(reviewer) or _progress_derived_label(reviewer)
            rows.append((label, points))
    return rows


def _top_reviewers_from_classification(
    round_dirs: list[Path],
    *,
    top_n: int,
    label_map: dict[str, str] | None = None,
) -> list[tuple[str, float]]:
    """Whole-run Top-reviewers aggregated from per-round findings-classification.tsv."""
    counts: dict[str, float] = {}
    active_bonus = voting.unique_finder_bonus_from_env()
    for round_dir in round_dirs:
        for reviewer, points in _accepted_reviewers_from_classification(
            round_dir / "findings-classification.tsv",
            round_dirs=round_dirs,
            label_map=label_map,
            active_bonus=active_bonus,
        ):
            counts[reviewer] = counts.get(reviewer, 0) + points
    return list(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n])

def _collector_failure_records(collector: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for block in re.split(r"\n\s*\n", collector):
        tool = ""
        status = ""
        reviewer_file = ""
        for line in block.splitlines():
            key, sep, value = line.partition("=")
            if not sep:
                continue
            if key == "TOOL":
                tool = value
            elif key == "STATUS":
                status = value
            elif key == "REVIEWER_FILE":
                reviewer_file = value
        if status and status != "OK":
            records.append((tool, Path(reviewer_file).name))
    return records


def _failed_reviewers(round_dirs: list[Path], *, label_map: dict[str, str]) -> tuple[int, list[tuple[str, int]]]:
    counts: dict[str, int] = {}
    total = 0
    for round_dir in round_dirs:
        collector = str(_read_json_object(round_dir / "round-meta.json").get("collector") or "")
        for tool, basename in _collector_failure_records(collector):
            label = label_map.get(basename)
            if not label:
                label = _progress_derived_label(basename)
                if tool and "/" in label:
                    label = tool + label[label.index("/") :]
            counts[label] = counts.get(label, 0) + 1
            total += 1
    return total, sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _render_phase_gantt(
    round_dirs: list[Path],
    *,
    timing_ledger: Path | None,
    rounds: list[_PhaseRound],
    label_map: dict[str, str],
) -> str:
    if timing_ledger is None or not timing_ledger.is_file():
        return ""
    sections: list[str] = []
    round_by_num = {row.number: row for row in rounds}
    for round_dir in round_dirs:
        round_num = _round_number(round_dir) or 0
        phase_round = round_by_num.get(round_num)
        if phase_round is None or phase_round.gantt_window is None:
            continue
        start_s, end_s = phase_round.gantt_window
        rows = _progress_vendor_rows(
            timing_ledger,
            start_s,
            end_s,
            label_map,
            skip_ci=True,
            require_complete_status=False,
        )
        sections.append(f"### Round {round_num} reviewer timing\n")
        if rows:
            chart = render_gantt(start_s, end_s, rows)
            if chart:
                span = end_s - start_s
                sections.append(
                    "```\n"
                    f"Round {round_num} reviewer timing  ·  window 0:00-{format_mss(span)} ({span}s)\n"
                    f"{chart}\n"
                    "```\n"
                )
            else:
                sections.append("No reviewer timing tasks overlapped this round.\n")
        else:
            sections.append("No reviewer timing tasks overlapped this round.\n")
    return "\n".join(sections).strip("\n") + ("\n\n" if sections else "")


def render_phase_detail(
    rounds_root: Path,
    skill: str,
    *,
    timing_ledger: Path | None = None,
    token_ledger: Path | None = None,
    findings_file: Path | None = None,
    top_n: int = 7,
    gantt_enabled: bool = True,
) -> str:
    if skill not in {"implement", "design"}:
        raise ValueError("skill must be implement or design")
    if not rounds_root.is_dir() or not os.access(rounds_root, os.R_OK | os.X_OK):
        return ""
    top_n = top_n if top_n > 0 else 7
    round_dirs = _completed_round_dirs(rounds_root)
    if not round_dirs:
        return "## Review Phase Detail\n\nNo review rounds completed.\n"
    label_map = _progress_label_map(round_dirs)
    phase_rounds = [
        _phase_round_from_meta(
            round_dir,
            skill=skill,
            timing_ledger=timing_ledger if timing_ledger is not None and timing_ledger.is_file() else None,
            token_ledger=token_ledger if token_ledger is not None and token_ledger.is_file() else None,
        )
        for round_dir in round_dirs
    ]
    total_time = sum(row.seconds or 0 for row in phase_rounds)
    any_time = any(row.seconds is not None for row in phase_rounds)
    costs = [float(row.cost[1:]) for row in phase_rounds if row.cost.startswith("$")]
    if _classification_tsv_available(round_dirs):
        top_reviewers = _top_reviewers_from_classification(round_dirs, top_n=top_n, label_map=label_map)
    else:
        top_reviewers = _top_reviewers(findings_file, label_map=label_map, top_n=top_n)
    fail_total, failures = _failed_reviewers(round_dirs, label_map=label_map)
    lines = [
        "## Review Phase Detail",
        "",
        "| Round | Suggestions | Accepted | OOS proposed | OOS accepted | Time | Cost | Reviewers |",
        "|--:|--:|--:|--:|--:|:--|--:|--:|",
    ]
    lines.extend(
        (
            f"| {row.number} | {row.suggestions} | {row.accepted} | {row.oos_proposed} | "
            f"{row.oos_accepted} | {_fmt_hms(row.seconds)} | {row.cost} | {row.reviewers} |"
        )
        for row in phase_rounds
    )
    total_cost = f"${sum(costs):.2f}" if costs else "—"
    lines.append(
        f"| **Total (round-sum)** | **{sum(row.suggestions for row in phase_rounds)}** | "
        f"**{sum(row.accepted for row in phase_rounds)}** | "
        f"**{sum(row.oos_proposed for row in phase_rounds)}** | "
        f"**{sum(row.oos_accepted for row in phase_rounds)}** | "
        f"**{_fmt_hms(total_time if any_time else None)}** | **{total_cost}** | "
        f"**{sum(row.reviewers for row in phase_rounds)}** |"
    )
    lines.append("")
    lines.append(
        "_The Total (round-sum) row adds up the per-round Suggestions and Accepted: when the "
        "review loop re-raises the same finding across rounds, that finding is counted once per "
        "round, so the round-sum can exceed the number of distinct findings. Top reviewers counts "
        "per-round accepted-point scores the same way._"
    )
    lines.append("")
    # Issue #4882: decompose the raw per-finding "Suggestions" count into the canonical scope-aware
    # split so "18 suggestions" reconciles with the headline "X/Y accepted" (in-scope only).
    decomp_segments: list[str] = []
    for row in phase_rounds:
        if row.inscope is None:
            continue
        oos = row.oos_total or 0
        seg = (
            f"round {row.number}: {row.inscope + oos} finding(s) = {row.inscope} in-scope "
            f"(voted; matches the headline X/Y accepted) + {oos} out-of-scope"
        )
        if row.nit_pruned:
            seg += f" (incl. {row.nit_pruned} nit-pruned)"
        decomp_segments.append(seg)
    if decomp_segments:
        lines.append(
            "_Finding decomposition (canonical, scope-aware): "
            + "; ".join(decomp_segments)
            + ". The Suggestions and OOS columns above count findings by finding id (raw per-finding) "
            "and can disagree with this scope-aware split when findings are reclassified out-of-scope "
            "after voting; round-meta.json records both raw (`tally`) and canonical (`tally_canonical`) "
            "counts so downstream joins do not contradict._"
        )
        lines.append("")
    if gantt_enabled:
        gantt = _render_phase_gantt(
            round_dirs,
            timing_ledger=timing_ledger if timing_ledger is not None and timing_ledger.is_file() else None,
            rounds=phase_rounds,
            label_map=label_map,
        )
        if gantt:
            lines.extend(gantt.rstrip("\n").splitlines())
            lines.append("")
    lines.append("**Top reviewers** (by per-round accepted-point score, whole run):")
    if top_reviewers:
        for index, (label, count) in enumerate(top_reviewers, start=1):
            lines.append(f"{index}. {label} — {voting.format_score(count)}")
    else:
        lines.append("- (no accepted-point score attributed to a reviewer slot)")
    lines.append("")
    lines.append(f"**Reviewer slot failures**: {fail_total}")
    for label, count in failures:
        lines.append(f"- {label}: {count}")
    return "\n".join(lines) + "\n"


def _render_phase_detail_best_effort(
    rounds_root: Path,
    *,
    skill: str,
    timing_ledger: Path | None = None,
    token_ledger: Path | None = None,
    findings_file: Path | None = None,
    top_n: int = 7,
    gantt_enabled: bool = True,
) -> str:
    # In-process render under a 15s wall-clock guard for live/final-summary callers;
    # explicit CLI rendering (render_phase_detail_main) calls render_phase_detail unbounded.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            render_phase_detail,
            rounds_root,
            skill,
            timing_ledger=timing_ledger,
            token_ledger=token_ledger,
            findings_file=findings_file,
            top_n=top_n,
            gantt_enabled=gantt_enabled,
        )
        return future.result(timeout=RENDER_PHASE_DETAIL_TIMEOUT_SECONDS)
    except Exception:  # pylint: disable=broad-except
        return ""
    finally:
        executor.shutdown(wait=False)


def _call_render_phase_detail(
    rounds_root: Path,
    skill: str,
    timing_ledger: Path | None,
    token_ledger: Path | None,
) -> str:
    text = _render_phase_detail_best_effort(
        rounds_root,
        skill=skill,
        timing_ledger=timing_ledger,
        token_ledger=token_ledger,
    )
    return _strip_md_for_terminal(text.strip()) if text.strip() else ""


def _progress_label_map_from_manifests(manifest_paths: list[Path]) -> dict[str, str]:
    label_map: dict[str, str] = {}
    for manifest in manifest_paths:
        try:
            lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for row in logging_util.iter_jsonl_dicts(lines):
            output = row.get("output")
            tool = row.get("tool")
            slot = row.get("slot")
            if not all(isinstance(value, str) and value for value in (output, tool, slot)):
                continue
            output_s = cast("str", output)
            tool_s = cast("str", tool)
            slot_s = cast("str", slot)
            label_map[Path(output_s).name] = f"{tool_s}/{slot_s}"
    return label_map


def _progress_label_map(round_dirs: list[Path]) -> dict[str, str]:
    return _progress_label_map_from_manifests([round_dir / "panel-manifest.ndjson" for round_dir in round_dirs])


def _progress_core_from_output(output: str) -> str:
    core = Path(output).name
    core = core.removesuffix(".txt")
    for suffix in ("-output-ns-retry", "-output", "-ns-retry"):
        if core.endswith(suffix):
            core = core[: -len(suffix)]
            break
    return core.lower()


def _progress_derived_label(output: str) -> str:
    core = _progress_core_from_output(output)
    vendor_match = r"cursor|codex|claude_sub|claude"
    if core == "aggregator":
        return "aggregator"
    if core == "scout-plan-manifest" or core.startswith("scout-plan-manifest."):
        return "scout"
    if core in {"codex", "cursor", "claude", "claude_sub"}:
        return core
    match = re.match(rf"^({vendor_match})-specialist-(.+)$", core)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    match = re.match(rf"^({vendor_match})-generalist$", core)
    if match:
        return f"{match.group(1)}/generalist"
    if core.startswith("dyn-"):
        return f"dynamic/{core[4:]}"
    match = re.match(rf"^({vendor_match})-(.*)$", core)
    if match:
        arch = match.group(2) or "panel"
        return f"{match.group(1)}/{arch}"
    if core in {"", "panel"}:
        return "panel/panel"
    return f"unknown/{core}"


def _derive_progress_label(
    output: str,
    vendor: str = "",
    kind: str = "",
    label_map: dict[str, str] | None = None,
) -> str:
    if kind in {"codex-review-fix", "codex-plan-autofix"}:
        return "codex/apply"
    if kind in {"cursor-review-fix", "cursor-plan-autofix"}:
        return "cursor/apply"
    basename = Path(output).name if output and output != "-" else ""
    labels = label_map or {}
    if basename and basename in labels:
        return labels[basename]
    derived = _progress_derived_label(basename) if basename else ""
    if derived in {"codex", "cursor", "claude", "claude_sub"} and kind and kind != "-":
        return f"{derived}/{kind}"
    if derived and derived != "unknown/-":
        return derived
    if vendor and kind:
        return f"{vendor}/{kind}"
    if vendor:
        return vendor
    return kind or "unknown"


def _is_ci_gantt_row(kind: str, output: str) -> bool:
    kind_l = (kind or "").lower()
    bn = Path(output).name.lower() if output else ""
    if kind_l in {"codex-ci", "cursor-ci", "claude-ci", "codex-ci-fix", "cursor-ci-fix", "claude-ci-fix"}:
        return True
    if kind_l.endswith(("-ci", "-ci-fix", "-ci-test")):
        return True
    if bn == "ci.out" or bn.endswith("-ci.out") or re.fullmatch(r"ci-fix-.*\.out", bn):
        return True
    return bn in {"claude.out", "codex.out", "cursor.out"}


# Coder fix-application task kinds, rendered as `*/apply` lanes. These rows
# start after the reviewer, aggregator, and voter slots, so a start-sorted
# truncation at PROGRESS_GANTT_ROW_CAP drops them; the cap helper reserves
# them so the chart always shows the coder applying review fixes (issue #5264).
_CODER_APPLY_TASK_KINDS: frozenset[str] = frozenset({
    "codex-review-fix", "cursor-review-fix", "claude-review-fix",
    "codex-plan-autofix", "cursor-plan-autofix",
})


def _cap_gantt_rows_reserving_apply(
    rows: list[tuple[int, int, str, bool]],
    *,
    cap: int,
) -> list[tuple[int, int, str, bool]]:
    """Cap rows to `cap` without dropping coder fix-application lanes.

    Reviewer, aggregator, and voter rows all start before the coder applies
    accepted fixes, so truncating the start-sorted list at `cap` silently
    drops the late-starting `*/apply` lane (issue #5264). Keep every apply
    row, fill the remaining budget with the earliest non-apply rows, and
    return the kept rows in chronological order. `rows` must already be
    sorted by (start_s, end_s, label).
    """
    if len(rows) <= cap:
        return rows
    apply_rows = [row for row in rows if row[3]]
    non_apply = [row for row in rows if not row[3]]
    budget = max(0, cap - len(apply_rows))
    kept = non_apply[:budget] + apply_rows
    kept.sort(key=lambda row: (row[0], row[1], row[2]))
    return kept


def _progress_vendor_rows(
    timing_ledger: Path,
    window_start_s: int,
    window_end_s: int,
    label_map: dict[str, str] | None = None,
    *,
    skip_ci: bool = False,
    require_complete_status: bool = True,
) -> list[GanttRow]:
    if window_end_s <= window_start_s:
        return []
    try:
        lines = timing_ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[tuple[int, int, str, bool]] = []
    for line in lines:
        cols = line.split("\t")
        if len(cols) < TIMING_VENDOR_MIN_COLS or cols[0] != "v1" or cols[1] != "vendor":
            continue
        status = cols[TIMING_VENDOR_STATUS_COL]
        if require_complete_status and status not in {"complete", "OK"}:
            continue
        try:
            start_s = int(cols[TIMING_VENDOR_START_COL])
            end_s = int(cols[TIMING_VENDOR_END_COL])
        except ValueError:
            continue
        if end_s <= window_start_s or start_s >= window_end_s:
            continue
        clamped_start = max(start_s, window_start_s)
        clamped_end = min(end_s, window_end_s)
        if clamped_end <= clamped_start:
            continue
        output = cols[TIMING_VENDOR_OUTPUT_COL] if len(cols) > TIMING_VENDOR_OUTPUT_COL else ""
        kind = cols[TIMING_VENDOR_KIND_COL]
        if skip_ci and _is_ci_gantt_row(kind, output):
            continue
        label = _derive_progress_label(output, cols[TIMING_VENDOR_VENDOR_COL], kind, label_map)
        rows.append((clamped_start, clamped_end, label, kind in _CODER_APPLY_TASK_KINDS))
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    capped = _cap_gantt_rows_reserving_apply(rows, cap=PROGRESS_GANTT_ROW_CAP)
    return [GanttRow(label, start_s, end_s) for start_s, end_s, label, _ in capped]


def _prior_immediate_round_end_s(timing_ledger: Path, skill: str, round_num: int) -> int | None:
    if round_num <= 1:
        return None
    try:
        lines = timing_ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    prior_round = str(round_num - 1)
    ends: list[int] = []
    for line in lines:
        cols = line.split("\t")
        if len(cols) < TIMING_ROUND_MIN_COLS:
            continue
        if (
            cols[0] != "v1"
            or cols[1] != "round"
            or cols[TIMING_ROUND_SKILL_COL] != skill
            or cols[TIMING_ROUND_ROUND_NUM_COL] != prior_round
        ):
            continue
        try:
            ends.append(int(cols[TIMING_ROUND_END_COL]))
        except ValueError:
            continue
    return max(ends) if ends else None


def _render_inflight_gantt(
    round_dir: Path,
    round_num: int,
    skill: str,
    timing_ledger: Path,
    label_manifest_paths: list[Path],
    window_start_s: int | None = None,
) -> str:
    start_s = _read_epoch_file(round_dir / "round-start-s")
    if start_s is None and round_num > 1:
        start_s = _prior_immediate_round_end_s(timing_ledger, skill, round_num)
    if start_s is None and round_num == 1:
        start_s = window_start_s
    if start_s is None:
        mtime = _path_mtime_s(round_dir)
        start_s = int(mtime) if mtime is not None else None
    if start_s is None:
        return ""
    end_s = int(time.time())
    if end_s <= start_s:
        return ""
    round_manifest_dirs = [path.parent for path in label_manifest_paths if path.name == "panel-manifest.ndjson"]
    label_map = (
        _progress_label_map(round_manifest_dirs)
        if len(round_manifest_dirs) == len(label_manifest_paths)
        else _progress_label_map_from_manifests(label_manifest_paths)
    )
    rows = _progress_vendor_rows(timing_ledger, start_s, end_s, label_map, skip_ci=True)
    if not rows:
        return ""
    chart = render_gantt(start_s, end_s, rows)
    if not chart:
        return ""
    span = end_s - start_s
    return (
        f"Round {round_num} reviewer timing\n\n"
        "```\n"
        f"Round {round_num} reviewer timing  ·  window 0:00-{format_mss(span)} ({span}s)\n"
        f"{chart}\n"
        "```"
    )


def _render_review_detail(implement_tmpdir: Path, run_id: str) -> str:
    timing = implement_tmpdir / "timing-ledger.tsv"
    return _call_render_phase_detail(
        _review_rounds_root(implement_tmpdir, run_id),
        "implement",
        timing if timing.is_file() else None,
        _latest_token_ledger(implement_tmpdir),
    )


def _render_step5(implement_tmpdir: Path, run_id: str, window_start_s: int | None = None) -> str:
    round_dir = _current_round_dir(implement_tmpdir)
    if round_dir is None:
        return ""
    round_num = _round_number(round_dir) or 0
    total = _count_lines(round_dir / "panel-manifest.ndjson")
    returned = _returned_reviewers(round_dir)
    header = (
        f"Step 5 code review — round {round_num} in progress\n"
        f"  reviewers: {returned}/{total} returned | elapsed: {_round_elapsed(round_dir)}"
    )
    selected_root = _review_rounds_root(implement_tmpdir, run_id)
    inflight = ""
    if not (round_dir / "round-meta.json").is_file():
        inflight = _render_inflight_gantt(
            round_dir,
            round_num,
            "implement",
            implement_tmpdir / "timing-ledger.tsv",
            [round_dir / "panel-manifest.ndjson"],
            window_start_s,
        )
    if _all_round_dirs_inflight(selected_root) or not _has_completed_round_meta(selected_root):
        return f"{header}\n\n{inflight}" if inflight else header
    detail = _render_review_detail(implement_tmpdir, run_id)
    parts = [header]
    if detail:
        parts.append(detail)
    if inflight:
        parts.append(inflight)
    return "\n\n".join(parts)


def _round_dir_is_fresh(round_dir: Path, mark_ts: int | None) -> bool:
    start_file = round_dir / "round-start-s"
    if start_file.is_file():
        start_s = _read_epoch_file(start_file)
        if start_s is not None and (mark_ts is None or start_s > mark_ts):
            return True
    if mark_ts is None:
        return round_dir.is_dir()
    try:
        for child in round_dir.iterdir():
            try:
                if child.is_file() and child.stat().st_mtime > mark_ts:
                    return True
            except OSError:
                continue
    except OSError:
        pass
    return False


def _render_implement(run: LiveRun) -> str:
    tmpdir = run.tmpdir
    ledger = tmpdir / "timing-ledger.tsv"
    step_label, start_s = _latest_timing_mark(ledger)
    step5_start_s = _latest_timing_mark_for_label(ledger, lambda label: "Step 5" in label)
    phase = _kv_value(tmpdir / "ship-pr-state.sh", "PHASE")
    if (tmpdir / "ship-pr-state.sh").is_file():
        return _render_ship_pr(tmpdir)
    done_marker = tmpdir / "progress" / "done"
    if not done_marker.exists():
        if "Step 5" in step_label or (not step_label and not phase):
            report = _render_step5(tmpdir, _resolve_run_id(tmpdir), step5_start_s)
            if report:
                return report
        else:
            round_dir = _current_round_dir(tmpdir)
            if round_dir is not None and _round_dir_is_fresh(round_dir, start_s):
                report = _render_step5(tmpdir, _resolve_run_id(tmpdir), step5_start_s)
                if report:
                    return report + "\nnote: step marks stale; phase inferred from round artifacts"
    return _render_generic("implement", step_label, start_s, tmpdir)


def _is_design_plan_review_step(step_label: str) -> bool:
    return (
        re.match(
            r"^(?:design\s+)?Step\s+3\s+(?:—|--)\s+(?:plan review|auto-continuation entry)(?:\b|(?:\s|—|-).*)$",
            step_label,
        )
        is not None
    )


def _read_epoch_file(path: Path) -> int | None:
    if path.is_symlink():
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _path_mtime_s(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _manifest_output_paths(manifest: Path) -> list[Path]:
    paths: list[Path] = []
    try:
        lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return paths
    for row in logging_util.iter_jsonl_dicts(lines):
        output = row.get("output")
        if isinstance(output, str) and output:
            paths.append(Path(output))
    return paths


def _paths_file_output_paths(paths_file: Path) -> list[Path]:
    try:
        lines = paths_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [Path(line.strip()) for line in lines if line.strip()]


def _count_fresh_nonempty_paths(paths: list[Path], freshness_floor: float) -> int:
    seen: set[str] = set()
    count = 0
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size <= 0 or stat.st_mtime < freshness_floor:
            continue
        count += 1
    return count


def _fresh_output_sidecar(manifest: Path) -> Path | None:
    sidecar = Path(f"{manifest}.output-files")
    manifest_mtime = _path_mtime_s(manifest)
    sidecar_mtime = _path_mtime_s(sidecar)
    if manifest_mtime is None or sidecar_mtime is None:
        return None
    if sidecar_mtime < manifest_mtime:
        return None
    try:
        if sidecar.stat().st_size <= 0:
            return None
    except OSError:
        return None
    return sidecar


def _design_round_start_s(round_dir: Path) -> int | None:
    return _read_epoch_file(round_dir / "round-start-s")


def _design_manifest_freshness_floor(round_dir: Path, step_start_s: int | None) -> float | None:
    anchors: list[float] = []
    if step_start_s is not None:
        anchors.append(float(step_start_s))
    round_start_s = _design_round_start_s(round_dir)
    if round_start_s is not None:
        anchors.append(float(round_start_s))
    if anchors:
        return max(anchors)
    return _path_mtime_s(round_dir)


def _fresh_design_round_manifest(round_dir: Path, step_start_s: int | None) -> Path | None:
    manifest = round_dir / "panel-manifest.ndjson"
    if _count_lines(manifest) == 0:
        return None
    floor = _design_manifest_freshness_floor(round_dir, step_start_s)
    manifest_mtime = _path_mtime_s(manifest)
    if floor is None or manifest_mtime is None or manifest_mtime < floor:
        return None
    return manifest


def _has_nonempty_output_at_least_as_new_as(manifest: Path, threshold: float) -> bool:
    sidecar = _fresh_output_sidecar(manifest)
    paths = _paths_file_output_paths(sidecar) if sidecar is not None else _manifest_output_paths(manifest)
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size > 0 and stat.st_mtime >= threshold:
            return True
    return False


def _fresh_design_root_manifest(
    design_tmpdir: Path,
    round_dir: Path,
    step_start_s: int | None,
) -> Path | None:
    manifest = design_tmpdir / "plan-review-slots.ndjson"
    if _count_lines(manifest) == 0:
        return None
    floor = _design_manifest_freshness_floor(round_dir, step_start_s)
    manifest_mtime = _path_mtime_s(manifest)
    if floor is None or manifest_mtime is None or manifest_mtime < floor:
        return None
    if _design_round_start_s(round_dir) is None:
        round_dir_mtime = _path_mtime_s(round_dir)
        if (
            round_dir_mtime is not None
            and manifest_mtime < round_dir_mtime
            and not _has_nonempty_output_at_least_as_new_as(manifest, round_dir_mtime)
        ):
            return None
    return manifest


def _design_panel_manifest(
    design_tmpdir: Path,
    round_dir: Path,
    step_start_s: int | None,
) -> Path | None:
    round_manifest = _fresh_design_round_manifest(round_dir, step_start_s)
    if round_manifest is not None:
        return round_manifest
    return _fresh_design_root_manifest(design_tmpdir, round_dir, step_start_s)


def _design_output_freshness_floor(
    design_tmpdir: Path,
    round_dir: Path,
    manifest: Path,
    step_start_s: int | None,
) -> float:
    anchors: list[float] = []
    if step_start_s is not None:
        anchors.append(float(step_start_s))
    round_start_s = _design_round_start_s(round_dir)
    if round_start_s is not None:
        anchors.append(float(round_start_s))
    manifest_mtime = _path_mtime_s(manifest) or 0.0
    if manifest == design_tmpdir / "plan-review-slots.ndjson":
        anchors.append(manifest_mtime)
        return max(anchors) if anchors else manifest_mtime
    return max(anchors) if anchors else manifest_mtime


def _design_returned_reviewers(
    design_tmpdir: Path,
    round_dir: Path,
    manifest: Path,
    step_start_s: int | None,
) -> int:
    total = _count_lines(manifest)
    if total <= 0:
        return 0
    sidecar = _fresh_output_sidecar(manifest)
    paths = _paths_file_output_paths(sidecar) if sidecar is not None else _manifest_output_paths(manifest)
    freshness_floor = _design_output_freshness_floor(design_tmpdir, round_dir, manifest, step_start_s)
    return min(total, _count_fresh_nonempty_paths(paths, freshness_floor))


def _fresh_design_voter_manifest(
    design_tmpdir: Path, step_start_s: int | None, round_dir: Path | None = None
) -> Path | None:
    """Return plan-voter-slots.ndjson when non-empty and fresh relative to round/step start."""
    manifest = design_tmpdir / "plan-voter-slots.ndjson"
    if _count_lines(manifest) == 0:
        return None
    if round_dir is not None:
        floor: float | None = _design_manifest_freshness_floor(round_dir, step_start_s)
    elif step_start_s is not None:
        floor = float(step_start_s)
    else:
        floor = None
    if floor is not None:
        manifest_mtime = _path_mtime_s(manifest)
        if manifest_mtime is not None and manifest_mtime < floor:
            return None
    return manifest


def _design_returned_voters(voter_manifest: Path, step_start_s: int | None) -> int:
    """Count returned external voter outputs (Voters 2 and 3) from voter_manifest."""
    total = _count_lines(voter_manifest)
    if total <= 0:
        return 0
    sidecar = _fresh_output_sidecar(voter_manifest)
    paths = _paths_file_output_paths(sidecar) if sidecar is not None else _manifest_output_paths(voter_manifest)
    manifest_mtime = _path_mtime_s(voter_manifest) or 0.0
    floor = max(float(step_start_s), manifest_mtime) if step_start_s is not None else manifest_mtime
    return min(total, _count_fresh_nonempty_paths(paths, floor))


def _design_elapsed(round_dir: Path, step_start_s: int | None) -> str:
    round_start_s = _design_round_start_s(round_dir)
    if round_start_s is not None:
        return _human_elapsed(round_start_s)
    round_mtime = _path_mtime_s(round_dir)
    if round_mtime is not None:
        return _human_elapsed(int(round_mtime))
    return _human_elapsed(step_start_s)


def _render_design_review_detail(design_tmpdir: Path) -> str:
    timing = design_tmpdir / "timing-ledger.tsv"
    return _call_render_phase_detail(
        design_tmpdir / "plan-review",
        "design",
        timing if timing.is_file() else None,
        _latest_token_ledger(design_tmpdir),
    )


def _render_design_plan_review(design_tmpdir: Path, start_s: int | None) -> str:
    round_dir = _current_round_dir(design_tmpdir / "plan-review")
    if round_dir is None:
        return ""
    manifest = _design_panel_manifest(design_tmpdir, round_dir, start_s)
    if manifest is None:
        return ""
    round_num = _round_number(round_dir) or 0
    total = _count_lines(manifest)
    returned = _design_returned_reviewers(design_tmpdir, round_dir, manifest, start_s)
    voter_manifest = _fresh_design_voter_manifest(design_tmpdir, start_s, round_dir)
    if voter_manifest is not None:
        voter_floor = _path_mtime_s(voter_manifest) or 0.0
        claude_voter_floor = voter_floor
        if start_s is not None:
            voter_floor = max(float(start_s), voter_floor)
            claude_voter_floor = float(start_s)
        voter_external_total = _count_lines(voter_manifest)
        voter_external_returned = _design_returned_voters(voter_manifest, start_s)
        claude_vote_path = design_tmpdir / "claude-vote-output.txt"
        try:
            claude_stat = claude_vote_path.stat()
            claude_done = 1 if claude_stat.st_size > 0 and claude_stat.st_mtime >= claude_voter_floor else 0
        except OSError:
            claude_done = 0
        voter_total = voter_external_total + 1
        voter_returned = voter_external_returned + claude_done
        review_state = "complete" if returned >= total else "in progress"
        header = (
            f"Step 3 plan review — round {round_num} {review_state}; plan vote in progress\n"
            f"  reviewers: {returned}/{total} | voters: {voter_returned}/{voter_total} returned"
            f" | elapsed: {_design_elapsed(round_dir, start_s)}"
        )
    else:
        claude_vote_path = design_tmpdir / "claude-vote-output.txt"
        claude_vote_floor = float(start_s) if start_s is not None else 0.0
        claude_is_active = False
        claude_done = 0
        try:
            claude_stat = claude_vote_path.stat()
            if claude_stat.st_mtime >= claude_vote_floor:
                claude_is_active = True
                claude_done = 1 if claude_stat.st_size > 0 else 0
        except OSError:
            pass
        if claude_is_active:
            review_state = "complete" if returned >= total else "in progress"
            header = (
                f"Step 3 plan review — round {round_num} {review_state}; plan vote in progress\n"
                f"  reviewers: {returned}/{total} | voters: {claude_done}/1 returned"
                f" | elapsed: {_design_elapsed(round_dir, start_s)}"
            )
        else:
            header = (
                f"Step 3 plan review — round {round_num} in progress\n"
                f"  reviewers: {returned}/{total} returned | elapsed: {_design_elapsed(round_dir, start_s)}"
            )
    plan_review_root = design_tmpdir / "plan-review"
    inflight = ""
    if not (round_dir / "round-meta.json").is_file():
        inflight = _render_inflight_gantt(
            round_dir,
            round_num,
            "design",
            design_tmpdir / "timing-ledger.tsv",
            [manifest],
            start_s,
        )
    if _all_round_dirs_inflight(plan_review_root) or not _has_completed_round_meta(plan_review_root):
        return f"{header}\n\n{inflight}" if inflight else header
    detail = _render_design_review_detail(design_tmpdir)
    parts = [header]
    if detail:
        parts.append(detail)
    if inflight:
        parts.append(inflight)
    return "\n\n".join(parts)


def _render_design(run: LiveRun) -> str:
    ledger = run.tmpdir / "timing-ledger.tsv"
    step_label, start_s = _latest_timing_mark(ledger)
    plan_review_start_s = _latest_timing_mark_for_label(ledger, _is_design_plan_review_step)
    if _is_design_plan_review_step(step_label):
        report = _render_design_plan_review(run.tmpdir, plan_review_start_s)
        if report:
            return report
    else:
        round_dir = _current_round_dir(run.tmpdir / "plan-review")
        if round_dir is not None and _round_dir_is_fresh(round_dir, start_s):
            report = _render_design_plan_review(run.tmpdir, plan_review_start_s)
            if report:
                return report + "\nnote: step marks stale; phase inferred from round artifacts"
    return _render_generic("design", step_label, start_s, run.tmpdir)


def _report(cwd: str) -> str:
    run = _discover_live_run(cwd)
    if run is None:
        return ""
    if run.skill == "implement":
        return _render_implement(run)
    return _render_design(run)


def _parse_tally_md(path: Path) -> tuple[int, int, int, int, int, int]:
    accepted = rejected = neutral = exonerated = oos_accepted = oos_rejected = 0
    in_findings = False
    for line in _read_lines_best_effort(path):
        if line.startswith("## Findings"):
            in_findings = True
            continue
        if in_findings and line.startswith("## "):
            in_findings = False
        if not in_findings or "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < MIN_MARKDOWN_TABLE_PARTS:
            continue
        item = parts[1] if len(parts) > 1 else ""
        result = parts[-2] if len(parts) >= MD_RESULT_COL_FROM_END else ""
        if not result or set(result) <= {"-"}:
            result = parts[-3] if len(parts) >= MD_FALLBACK_RESULT_COL_FROM_END else ""
        invalid_item = not item or item == "Item" or set(item) <= {"-"}
        invalid_result = not result or result == "Result" or set(result) <= {"-"}
        if invalid_item or invalid_result:
            continue
        if re.fullmatch(r"FINDING_[0-9A-Za-z_]+", item):
            if result == "accepted":
                accepted += 1
            elif result == "rejected":
                rejected += 1
            elif result == "neutral":
                neutral += 1
            elif result == "exonerated":
                exonerated += 1
        elif re.fullmatch(r"OOS_[0-9A-Za-z_]+", item):
            if result == "accepted":
                oos_accepted += 1
            else:
                oos_rejected += 1
    return accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected


def _parse_classification_tsv(path: Path) -> tuple[int, int, int, int, int, int]:
    accepted = rejected = neutral = exonerated = oos_accepted = oos_rejected = 0
    lines = _read_lines_best_effort(path)
    if not lines:
        return accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected
    header = [col.strip() for col in lines[0].split("\t")]
    for line in lines[1:]:
        raw_cols = [col.strip() for col in line.split("\t")]
        if len(raw_cols) < MIN_TSV_RESULT_COLS:
            continue
        cols = {name: raw_cols[idx] if idx < len(raw_cols) else "" for idx, name in enumerate(header)}
        item = cols.get("finding_id", raw_cols[0])
        result = cols.get("voting_result", raw_cols[2] if len(raw_cols) >= MIN_TSV_RESULT_COLS else "")
        in_scope = _classification_row_in_scope(cols, header)
        if in_scope and re.fullmatch(r"FINDING_[0-9A-Za-z_]+", item):
            if result == "accepted":
                accepted += 1
            elif result == "rejected":
                rejected += 1
            elif result == "neutral":
                neutral += 1
            elif result == "exonerated":
                exonerated += 1
        elif result:
            if result == "accepted":
                oos_accepted += 1
            else:
                oos_rejected += 1
    return accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected

def _tsv_has_data_rows(path: Path) -> bool:
    return any(line.strip() for line in _read_lines_best_effort(path)[1:])


def _round_counts(round_dir: Path) -> tuple[tuple[int, int, int, int, int, int], str]:
    counts: tuple[int, int, int, int, int, int] | None = None
    source = ""
    tally = round_dir / "voting-tally.md"
    classification = round_dir / "findings-classification.tsv"
    md_counts = (0, 0, 0, 0, 0, 0)
    if tally.is_file():
        md_counts = _parse_tally_md(tally)
        counts = md_counts
        source = "md"
    if classification.is_file():
        tsv_counts = _parse_classification_tsv(classification)
        if counts is None or (md_counts == (0, 0, 0, 0, 0, 0) and _tsv_has_data_rows(classification)):
            counts = tsv_counts
            source = "tsv"
    return counts or (0, 0, 0, 0, 0, 0), source


def _oos_result_rows(round_dir: Path, source: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if source == "md":
        in_findings = False
        for line in _read_lines_best_effort(round_dir / "voting-tally.md"):
            if line.startswith("## Findings"):
                in_findings = True
                continue
            if in_findings and line.startswith("## "):
                in_findings = False
            if not in_findings or "|" not in line:
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < MIN_MARKDOWN_TABLE_PARTS:
                continue
            item = parts[1]
            result = parts[-2] if parts[-2] and set(parts[-2]) != {"-"} else parts[-3]
            if re.fullmatch(r"OOS_[0-9A-Za-z_]+", item) and result:
                rows.append((item, result))
    elif source == "tsv":
        for line in _read_lines_best_effort(round_dir / "findings-classification.tsv")[1:]:
            cols = [col.strip() for col in line.split("\t")]
            if len(cols) >= MIN_TSV_RESULT_COLS and re.fullmatch(r"OOS_[0-9A-Za-z_]+", cols[0]) and cols[2]:
                rows.append((cols[0], cols[2]))
    return rows


def _extract_oos_block(round_dir: Path, oos_id: str) -> str:
    pattern = re.compile(rf"(?ms)^### {re.escape(oos_id)}:.*?(?=^### |\Z)")
    for name in ("findings-oos.md", "findings.md", "oos.md", "findings-in-scope.md"):
        path = round_dir / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = pattern.search(text)
        if match:
            return match.group(0)
    return ""


def _adjust_design_security_oos(
    round_dir: Path,
    counts: tuple[int, int, int, int, int, int],
    source: str,
) -> tuple[int, int, int, int, int, int]:
    accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected = counts
    for oos_id, result in _oos_result_rows(round_dir, source):
        block = _extract_oos_block(round_dir, oos_id)
        if not block:
            continue
        tmp = round_dir / f".oos-sec-{oos_id}.tmp"
        try:
            tmp.write_text(block, encoding="utf-8")
            is_security = voting.is_security_block(tmp)
        except Exception:  # pylint: disable=broad-except
            is_security = False
        finally:
            with contextlib.suppress(OSError):
                tmp.unlink()
        if not is_security:
            continue
        if result == "accepted":
            oos_accepted = max(0, oos_accepted - 1)
        else:
            oos_rejected = max(0, oos_rejected - 1)
    return accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected


def _materialize_design_panel_manifest(round_dir: Path) -> int:
    slots_src = round_dir / "plan-review-slots.ndjson"
    if not slots_src.is_file():
        slots_src = round_dir.parent.parent / "plan-review-slots.ndjson"
    panel_tmp = round_dir / "panel-manifest.ndjson.tmp"
    count = 0
    try:
        with panel_tmp.open("w", encoding="utf-8") as dst:
            for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(slots_src)):
                slot = str(row.get("slot") or "")
                tool = str(row.get("tool") or "")
                output = str(row.get("output") or "")
                if not (slot or tool or output):
                    continue
                dst.write(json.dumps({"slot": slot, "tool": tool, "output": output}, separators=(",", ":")) + "\n")
                count += 1
        panel_tmp.replace(round_dir / "panel-manifest.ndjson")
    except OSError:
        with contextlib.suppress(OSError):
            panel_tmp.unlink()
        return 0
    return count


def _count_panel_manifest(path: Path) -> int:
    count = 0
    for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(path)):
        if any(row.get(k) for k in ("slot", "tool", "output")):
            count += 1
    return count


def _read_simple_env(path: Path) -> dict[str, str]:
    try:
        text = larch_io.read_text(path, errors="replace", default="")
    except OSError:
        return {}
    return larch_io.parse_kv(text)


def _round_meta_object(
    counts: tuple[int, int, int, int, int, int],
    panel_count: int,
    *,
    collector: str = "",
    revise: dict[str, str | None] | None = None,
    canonical: tuple[int, int, int, int, int, int] | None = None,
    nit_pruned: int = 0,
) -> dict[str, object]:
    accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected = counts
    obj: dict[str, object] = {
        "tally": {
            "ACCEPTED_COUNT": str(accepted),
            "REJECTED_COUNT": str(rejected),
            "EXONERATED_COUNT": str(exonerated),
            "NEUTRAL_COUNT": str(neutral),
            "OOS_ACCEPTED_COUNT": str(oos_accepted),
            "OOS_REJECTED_COUNT": str(oos_rejected),
        },
        "summary": {"panel": {"total_slot_count": panel_count}},
        "collector": collector,
    }
    # Issue #4882: the raw `tally` above counts findings by id-prefix (FINDING_/OOS_), so a
    # nit-pruned [OUT_OF_SCOPE] FINDING_N is miscounted as in-scope rejected. Record the canonical,
    # scope-aware decomposition alongside it (matching code-review-tally.json) so the run-summary can
    # reconcile the two and downstream joins do not see a contradiction.
    if canonical is not None:
        c_accepted, c_rejected, c_neutral, c_exonerated, c_oos_accepted, c_oos_rejected = canonical
        obj["tally_canonical"] = {
            "ACCEPTED_COUNT": str(c_accepted),
            "REJECTED_COUNT": str(c_rejected),
            "EXONERATED_COUNT": str(c_exonerated),
            "NEUTRAL_COUNT": str(c_neutral),
            "OOS_ACCEPTED_COUNT": str(c_oos_accepted),
            "OOS_REJECTED_COUNT": str(c_oos_rejected),
        }
        obj["nit_pruned_count"] = str(nit_pruned)
    if revise is not None:
        obj["revise"] = revise
    return obj


def _canonical_decomposition(round_dir: Path) -> tuple[tuple[int, int, int, int, int, int] | None, int]:
    """Issue #4882: scope-aware in-scope/OOS counts from the classification TSV, plus nit-pruned.

    The classification TSV carries the authoritative ``scope`` column, so it separates in-scope
    findings from out-of-scope ones (including nit-pruned ``[OUT_OF_SCOPE] FINDING_N`` blocks that
    keep a ``FINDING_`` id). Returns ``(None, 0)`` when no classification data is available (e.g.
    design plan-review rounds), leaving the raw tally as the only recorded view.
    """
    tsv = round_dir / "findings-classification.tsv"
    if not tsv.is_file() or not _tsv_has_data_rows(tsv):
        return None, 0
    canonical = _parse_classification_tsv(tsv)
    nit_pruned = 0
    prune_env = round_dir / "prune-nit.env"
    if prune_env.is_file():
        raw = _read_simple_env(prune_env).get("PRUNED_COUNT", "")
        if raw.isdigit():
            nit_pruned = int(raw)
    return canonical, nit_pruned


def _design_collector_field(round_dir: Path, failure_count: int) -> str:
    """Build round-meta.json's ``collector`` field from real per-slot collector records.

    The collector writes ``collector-results.env`` (blank-line-separated
    ``KEY=VALUE`` records: ``REVIEWER_FILE``/``TOOL``/``STATUS``/...) at the design
    tmpdir root; mirror
    ``_materialize_design_panel_manifest`` by checking the round dir first, then the
    design root. Each non-OK record becomes a ``TOOL``/``STATUS``/``REVIEWER_FILE``
    block carrying the real failing slot's tool and output basename, so the renderer
    resolves the true vendor/archetype instead of ``unknown/collector-failure-N``.
    Falls back to count-based placeholders only when no per-slot records are available.
    """
    if failure_count <= 0:
        return ""
    collector_env = round_dir / "collector-results.env"
    if not collector_env.is_file():
        collector_env = round_dir.parent.parent / "collector-results.env"
    records: list[str] = []
    collector_text = "\n".join(_read_lines_best_effort(collector_env))
    for record in collect_results.parse_collector_records(collector_text):
        status = record.get("STATUS", "")
        if status and status != "OK":
            tool = record.get("TOOL", "")
            reviewer_file = record.get("REVIEWER_FILE", "")
            records.append(f"TOOL={tool}\nSTATUS={status}\nREVIEWER_FILE={Path(reviewer_file).name}")
    if records:
        return "\n\n".join(records)
    return "\n\n".join(
        f"TOOL=unknown\nSTATUS=FAILED\nREVIEWER_FILE=collector-failure-{index}.txt"
        for index in range(1, failure_count + 1)
    )


def write_design_round_meta(round_dir: Path) -> int:
    if not round_dir.is_dir():
        return 0
    try:
        counts, source = _round_counts(round_dir)
        if source:
            counts = _adjust_design_security_oos(round_dir, counts, source)
        panel_count = _materialize_design_panel_manifest(round_dir)
        env = _read_simple_env(round_dir / "round-summary.env")
        failures = _as_int(env.get("COLLECT_FAILURE_COUNT"))
        collector = _design_collector_field(round_dir, failures)
        revise_env = _read_simple_env(round_dir / "revise" / "revise.env")
        meta = _round_meta_object(
            counts,
            panel_count,
            collector=collector,
            revise={
                "status": revise_env.get("REVISE_STATUS") or None,
                "tier": revise_env.get("REVISE_TIER") or None,
            },
        )
        tmp = round_dir / "round-meta.json.tmp"
        tmp.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        tmp.replace(round_dir / "round-meta.json")
    except Exception:  # pylint: disable=broad-except
        return 1
    return 0


def write_implement_round_meta(round_dir: Path) -> int:
    if not round_dir.is_dir():
        return 0
    try:
        counts, _source = _round_counts(round_dir)
        panel_count = _count_panel_manifest(round_dir / "panel-manifest.ndjson")
        canonical, nit_pruned = _canonical_decomposition(round_dir)
        meta = _round_meta_object(counts, panel_count, canonical=canonical, nit_pruned=nit_pruned)
        tmp = round_dir / "round-meta.json.tmp"
        tmp.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        tmp.replace(round_dir / "round-meta.json")
    except Exception:  # pylint: disable=broad-except
        return 1
    return 0


def render_phase_detail_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress render-phase-detail")
    parser.add_argument("--rounds-root", required=True)
    parser.add_argument("--findings-file")
    parser.add_argument("--timing-ledger")
    parser.add_argument("--token-ledger")
    parser.add_argument("--skill", choices=("implement", "design"), default="implement")
    parser.add_argument("--top-n", default="7")
    parser.add_argument("--no-gantt", action="store_true")
    parser.add_argument("--output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    top_n = int(args.top_n) if str(args.top_n).isdigit() else 7
    text = render_phase_detail(
        Path(args.rounds_root),
        args.skill,
        timing_ledger=Path(args.timing_ledger) if args.timing_ledger else None,
        token_ledger=Path(args.token_ledger) if args.token_ledger else None,
        findings_file=Path(args.findings_file) if args.findings_file else None,
        top_n=top_n,
        gantt_enabled=not args.no_gantt,
    )
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def write_design_round_meta_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress write-design-round-meta")
    parser.add_argument("--round-dir", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    return write_design_round_meta(Path(args.round_dir))


def write_implement_round_meta_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress write-implement-round-meta")
    parser.add_argument("--round-dir", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    return write_implement_round_meta(Path(args.round_dir))


def report_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="progress report", add_help=True)
    _ = parser.add_argument("--cwd", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        report = _report(args.cwd)
    except Exception:  # pylint: disable=broad-except
        return 0
    if report:
        print(report)
    return 0
