"""On-demand progress reports for live larch runs."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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


def _render_review_detail(implement_tmpdir: Path, run_id: str) -> str:
    script = Path(__file__).resolve().parent.parent / "scripts" / "render-review-phase-detail.sh"
    if not script.is_file():
        return ""
    rounds_root = _review_rounds_root(implement_tmpdir, run_id)
    argv = [str(script), "--rounds-root", str(rounds_root), "--skill", "implement"]
    timing = implement_tmpdir / "timing-ledger.tsv"
    if timing.is_file():
        argv.extend(["--timing-ledger", str(timing)])
    token_ledgers = sorted(implement_tmpdir.glob("larch-tokens-*.jsonl"), key=_path_mtime)
    if token_ledgers:
        argv.extend(["--token-ledger", str(token_ledgers[-1])])
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=6, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return _strip_md_for_terminal(result.stdout.strip())


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
    detail = _render_review_detail(implement_tmpdir, run_id)
    return f"{header}\n\n{detail}" if detail else header


def _render_implement(run: LiveRun) -> str:
    tmpdir = run.tmpdir
    step_label, start_s = _latest_timing_mark(tmpdir / "timing-ledger.tsv")
    phase = _kv_value(tmpdir / "ship-pr-state.sh", "PHASE")
    if (tmpdir / "ship-pr-state.sh").is_file() and phase in SHIP_PR_PHASES:
        return _render_ship_pr(tmpdir)
    done_marker = tmpdir / "progress" / "done"
    if not done_marker.exists() and ("Step 5" in step_label or (not step_label and not phase)):
        report = _render_step5(tmpdir, _resolve_run_id(tmpdir))
        if report:
            return report
    return _render_generic("implement", step_label, start_s, tmpdir)


def _render_design(run: LiveRun) -> str:
    step_label, start_s = _latest_timing_mark(run.tmpdir / "timing-ledger.tsv")
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
