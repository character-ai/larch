"""On-demand progress reports for live larch runs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from gantt import GanttRow, format_mss, render_gantt

TIMING_MARK_MIN_COLS = 5
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600

_MD_TABLE_SEP_RE = re.compile(r"^\|[ :\-|]+\|$")
_MD_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<![_\w])_([^_\n]+)_(?![_\w])")
_MD_HEADING_RE = re.compile(r"^#{1,6} ")
SHIP_PR_PHASES = frozenset({
    "checks",
    "ci-initial",
    "ci-merge",
    "pr-prep",
    "pr-create",
    "pr-push",
    "merge",
    "postmerge",
    "rebase",
    "rebase-failed",
    "stalled",
    "done",
})


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
    data: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return data
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", key):
            continue
        try:
            parsed = shlex.split(value, posix=True)
        except ValueError:
            parsed = [value]
        data[key] = parsed[0] if len(parsed) == 1 else value
    return data


def _kv_value(path: Path, key: str) -> str:
    return _read_env_file(path).get(key, "")


def _path_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


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
    return LiveRun("design", tmpdir, cwd, pointer, _path_mtime(pointer))


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
    return LiveRun("implement", tmpdir, cwd, pointer, _path_mtime(pointer))


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

TIMING_LEDGER_COLS = 13
TIMING_ROUND_N_COL = 5
TIMING_ROUND_START_COL = 6
TIMING_ROUND_END_COL = 7
TIMING_VENDOR_VENDOR_COL = 5
TIMING_VENDOR_KIND_COL = 6
TIMING_VENDOR_START_COL = 7
TIMING_VENDOR_END_COL = 8
TIMING_VENDOR_OUTPUT_COL = 10
PROGRESS_GANTT_ROW_CAP = 25


def _completed_round_dirs(rounds_root: Path) -> list[Path]:
    return [path for path in _round_dirs(rounds_root) if (path / "round-meta.json").is_file()]


def _basename(path: str) -> str:
    return Path(path).name


def _derive_progress_label(output: str, vendor: str, task_kind: str) -> str:
    core = _basename(output)
    for suffix in (".txt", "-output-ns-retry", "-output", "-ns-retry"):
        core = core.removesuffix(suffix)
    core = core.lower()
    for prefix in ("cursor-specialist-", "codex-specialist-", "claude_sub-specialist-", "claude-specialist-"):
        if core.startswith(prefix):
            return f"{prefix.split('-')[0]}/{core[len(prefix):]}"
    for prefix in ("cursor-", "codex-", "claude_sub-", "claude-"):
        if core.startswith(prefix):
            rest = core[len(prefix) :] or "panel"
            return f"{prefix[:-1]}/{rest}"
    if core in {"", "panel"}:
        return "panel/panel"
    if core:
        return f"unknown/{core}"
    return f"{vendor}/{task_kind}"


def _progress_label_map(round_dirs: list[Path]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for round_dir in round_dirs:
        for manifest in (round_dir / "panel-manifest.ndjson", round_dir / "plan-review-slots.ndjson"):
            try:
                lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines:
                if not line.strip():
                    continue
                try:
                    parsed: object = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(parsed, dict):
                    continue
                row = cast("dict[str, object]", parsed)
                output = row.get("output")
                tool = row.get("tool")
                slot = row.get("slot")
                if isinstance(output, str) and isinstance(tool, str) and isinstance(slot, str):
                    labels[_basename(output)] = f"{tool}/{slot}"
    return labels


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _timing_lines(timing_ledger: Path) -> list[list[str]]:
    try:
        lines = timing_ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[list[str]] = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) < TIMING_LEDGER_COLS or parts[0] != "v1":
            continue
        rows.append(parts)
    return rows


def _progress_round_windows(rows: list[list[str]]) -> dict[int, tuple[int, int]]:
    windows: dict[int, tuple[int, int]] = {}
    for parts in rows:
        if parts[1] != "round":
            continue
        round_n = _parse_int(parts[TIMING_ROUND_N_COL])
        start_s = _parse_int(parts[TIMING_ROUND_START_COL])
        end_s = _parse_int(parts[TIMING_ROUND_END_COL])
        if round_n is None or start_s is None or end_s is None or end_s <= start_s:
            continue
        old = windows.get(round_n)
        if old is None:
            windows[round_n] = (start_s, end_s)
        else:
            windows[round_n] = (min(old[0], start_s), max(old[1], end_s))
    return windows


def _progress_vendor_rows(
    rows: list[list[str]],
    *,
    window_start_s: int,
    window_end_s: int,
    labels: dict[str, str],
) -> list[GanttRow]:
    out: list[GanttRow] = []
    for parts in rows:
        if parts[1] != "vendor":
            continue
        start_s = _parse_int(parts[TIMING_VENDOR_START_COL])
        end_s = _parse_int(parts[TIMING_VENDOR_END_COL])
        if start_s is None or end_s is None:
            continue
        if end_s <= window_start_s or start_s >= window_end_s:
            continue
        clamped_start = max(start_s, window_start_s)
        clamped_end = min(end_s, window_end_s)
        if clamped_end <= clamped_start:
            continue
        output = parts[TIMING_VENDOR_OUTPUT_COL]
        label = labels.get(_basename(output)) or _derive_progress_label(
            output,
            parts[TIMING_VENDOR_VENDOR_COL],
            parts[TIMING_VENDOR_KIND_COL],
        )
        out.append(GanttRow(label, clamped_start, clamped_end))
    return sorted(out, key=lambda row: (row.start_s, row.end_s, row.label))[:PROGRESS_GANTT_ROW_CAP]


def _render_progress_timing_charts(rounds_root: Path, timing_ledger: Path) -> str:
    try:
        round_dirs = _completed_round_dirs(rounds_root)
        if not round_dirs or not timing_ledger.is_file():
            return ""
        rows = _timing_lines(timing_ledger)
        windows = _progress_round_windows(rows)
        labels = _progress_label_map(round_dirs)
        sections: list[str] = []
        for round_dir in round_dirs:
            round_n = _round_number(round_dir)
            if round_n is None or round_n not in windows:
                continue
            window_start_s, window_end_s = windows[round_n]
            chart_rows = _progress_vendor_rows(
                rows,
                window_start_s=window_start_s,
                window_end_s=window_end_s,
                labels=labels,
            )
            if not chart_rows:
                continue
            chart = render_gantt(window_start_s, window_end_s, chart_rows)
            if not chart:
                continue
            span = max(0, window_end_s - window_start_s)
            sections.append(
                "\n".join(
                    [
                        f"### Round {round_n} reviewer timing",
                        "",
                        "```",
                        f"Round {round_n} reviewer timing  ·  window 0:00-{format_mss(span)} ({span}s)",
                        chart,
                        "```",
                    ]
                )
            )
        return "\n\n".join(sections)
    except Exception:  # pylint: disable=broad-except
        return ""



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
    run_log_root = implement_tmpdir / "larch-logs" / "implement" / run_id if run_id else None
    if run_log_root is not None and run_log_root.is_dir() and _round_dirs(run_log_root):
        return run_log_root
    return implement_tmpdir


def _latest_token_ledger(tmpdir: Path) -> Path | None:
    try:
        token_ledgers = sorted(tmpdir.glob("larch-tokens-*.jsonl"), key=_path_mtime)
    except OSError:
        return None
    return token_ledgers[-1] if token_ledgers else None


def _call_render_phase_detail_script(
    rounds_root: Path,
    skill: str,
    timing_ledger: Path | None,
    token_ledger: Path | None,
) -> str:
    script = Path(__file__).resolve().parent.parent / "scripts" / "render-review-phase-detail.sh"
    if not script.is_file():
        return ""
    argv = [str(script), "--rounds-root", str(rounds_root), "--skill", skill, "--no-gantt"]
    if timing_ledger is not None and timing_ledger.is_file():
        argv.extend(["--timing-ledger", str(timing_ledger)])
    if token_ledger is not None and token_ledger.is_file():
        argv.extend(["--token-ledger", str(token_ledger)])
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=6, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return _strip_md_for_terminal(result.stdout.strip())


def _render_review_detail(implement_tmpdir: Path, run_id: str) -> str:
    rounds_root = _review_rounds_root(implement_tmpdir, run_id)
    timing = implement_tmpdir / "timing-ledger.tsv"
    detail = _call_render_phase_detail_script(
        rounds_root,
        "implement",
        timing if timing.is_file() else None,
        _latest_token_ledger(implement_tmpdir),
    )
    charts = _render_progress_timing_charts(rounds_root, timing)
    return "\n\n".join(part for part in (detail, charts) if part)


def _render_step5(implement_tmpdir: Path, run_id: str) -> str:
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
    if _all_round_dirs_inflight(selected_root):
        return header
    detail = _render_review_detail(implement_tmpdir, run_id)
    return f"{header}\n\n{detail}" if detail else header


def _round_dir_is_fresh(round_dir: Path, mark_ts: int | None) -> bool:
    if (round_dir / "round-start-s").is_file():
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
    step_label, start_s = _latest_timing_mark(tmpdir / "timing-ledger.tsv")
    phase = _kv_value(tmpdir / "ship-pr-state.sh", "PHASE")
    if (tmpdir / "ship-pr-state.sh").is_file() and phase in SHIP_PR_PHASES:
        return _render_ship_pr(tmpdir)
    done_marker = tmpdir / "progress" / "done"
    if not done_marker.exists():
        if "Step 5" in step_label or (not step_label and not phase):
            report = _render_step5(tmpdir, _resolve_run_id(tmpdir))
            if report:
                return report
        else:
            round_dir = _current_round_dir(tmpdir)
            if round_dir is not None and _round_dir_is_fresh(round_dir, start_s):
                report = _render_step5(tmpdir, _resolve_run_id(tmpdir))
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
    for line in lines:
        if not line.strip():
            continue
        try:
            parsed: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        row = cast("dict[str, object]", parsed)
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
    rounds_root = design_tmpdir / "plan-review"
    detail = _call_render_phase_detail_script(
        rounds_root,
        "design",
        timing if timing.is_file() else None,
        _latest_token_ledger(design_tmpdir),
    )
    charts = _render_progress_timing_charts(rounds_root, timing)
    return "\n\n".join(part for part in (detail, charts) if part)


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
    if _all_round_dirs_inflight(plan_review_root):
        return header
    detail = _render_design_review_detail(design_tmpdir)
    return f"{header}\n\n{detail}" if detail else header


def _render_design(run: LiveRun) -> str:
    step_label, start_s = _latest_timing_mark(run.tmpdir / "timing-ledger.tsv")
    if _is_design_plan_review_step(step_label):
        report = _render_design_plan_review(run.tmpdir, start_s)
        if report:
            return report
    else:
        round_dir = _current_round_dir(run.tmpdir / "plan-review")
        if round_dir is not None and _round_dir_is_fresh(round_dir, start_s):
            report = _render_design_plan_review(run.tmpdir, start_s)
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
