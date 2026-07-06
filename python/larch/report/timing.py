# ruff: noqa: PLC0415, SIM105, PERF402, S108, PLR2004, E702
# pylint: disable=all
"""Timing ledger, report, harness, and telemetry helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from collections.abc import Mapping

from larch.report import tokens

# Canonical allow-list for literal --timing-task-kind values; update with every new literal call site.
TIMING_TASK_KINDS_ALLOWED: frozenset[str] = frozenset({
    "codex-review", "cursor-review", "codex-review-generic", "cursor-review-generic",
    "codex-implement", "cursor-implement", "codex-review-fix", "cursor-review-fix", "claude-review-fix",
    "codex-ci", "cursor-ci", "claude-ci",
    "codex-ci-fix", "cursor-ci-fix", "claude-ci-fix",
    "claude-review", "cursor-brainstorm", "codex-brainstorm",
    "codex-plan-arch", "codex-plan-innovation", "codex-plan-pragmatic", "codex-plan-requirements",
    "cursor-plan-arch", "cursor-plan-innovation", "cursor-plan-pragmatic", "cursor-plan-requirements",
    "codex-plan-voter", "cursor-plan-voter", "claude-plan-voter", "claude-plan-draft",
    "claude-code-voter", "claude-plan-generic", "claude-decomp-generic", "claude-voter-1-parse-retry",
    "codex-plan-autofix", "cursor-plan-autofix", "gate-b-apply",
    "codex-review-voter", "cursor-review-voter",
    "claude-phase3-correctness", "claude-phase3-edge-cases", "claude-phase3-testing",
    "claude-phase3-structure", "claude-phase3-plan-fidelity", "claude-phase3-aggregator",
    "scout-dynamic-archetypes", "cursor-specialist-structure", "cursor-specialist-correctness",
    "cursor-specialist-testing", "cursor-specialist-edge-cases", "cursor-specialist-plan-fidelity",
    "codex-specialist-structure", "codex-specialist-correctness", "codex-specialist-testing",
    "codex-specialist-edge-cases", "codex-specialist-plan-fidelity", "cursor-phase1-correctness",
    "cursor-phase1-edge-cases", "cursor-phase1-testing", "cursor-phase2-correctness",
    "cursor-phase2-edge-cases", "cursor-phase2-testing", "codex-phase1-correctness",
    "codex-phase1-edge-cases", "codex-phase1-testing", "codex-phase2-correctness",
    "codex-phase2-edge-cases", "codex-phase2-testing", "codex-exec", "codex-plan-draft",
    "claude-relevant-checks", "claude-lint-fix", "vendor-misc", "implement-code-flow",
    "exec-issue-assessment", "rejected-analysis-verify",
})
TIMING_VENDOR_MIN_COLS = 13
TIMING_LOCK_TIMEOUT_S = 5.0
TIMING_VENDORS_ALLOWED: frozenset[str] = frozenset({"codex", "cursor", "claude"})
_TASK_KIND_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


@dataclass(frozen=True)
class TimingLedger:
    path: Path
    skill: str = "implement"

    def mark(self, step: str) -> None:
        row = ["v1", "mark", str(int(time.time())), _san(self.skill), _san(step), "-", "-", "-", "-", "-", "-", "-", "-"]
        self._append(row)

    def record_vendor_task(
        self,
        *,
        vendor: str,
        task_kind: str,
        start_s: float,
        end_s: float,
        output: str,
        exit_code: int = 0,
        status: str = "complete",
    ) -> None:
        if vendor not in TIMING_VENDORS_ALLOWED:
            msg = "vendor must be codex, cursor, or claude"
            raise ValueError(msg)
        if not _TASK_KIND_RE.fullmatch(task_kind):
            msg = f"malformed task-kind: {task_kind}"
            raise ValueError(msg)
        if task_kind not in TIMING_TASK_KINDS_ALLOWED:
            print(f"timing: WARNING: unknown task-kind: {task_kind}", file=sys.stderr)
        norm_status = {"OK": "complete", "ERROR": "signal", "TIMEOUT": "signal"}.get(status, status)
        if norm_status not in {"complete", "signal", "unknown"}:
            msg = "--status must be complete, signal, unknown, OK, ERROR, or TIMEOUT"
            raise ValueError(msg)
        start_i = int(start_s)
        end_i = int(end_s)
        duration = max(0, end_i - start_i)
        if end_i < start_i:
            norm_status = "unknown"
            print("timing: WARNING: end_s precedes start_s; clamping duration_s to 0", file=sys.stderr)
        row = [
            "v1", "vendor", str(int(time.time())), _san(self.skill), "-", _san(vendor), _san(task_kind),
            str(start_i), str(end_i), str(duration), _san(Path(output).name), str(int(exit_code)), norm_status,
        ]
        self._append(row)

    def record_round(
        self,
        *,
        skill: str,
        step: str,
        round_n: int,
        start_s: float,
        end_s: float,
        accepted: int,
        rejected: int,
        oos: int | None = None,
    ) -> None:
        if skill not in {"implement", "design"}:
            msg = "--skill must be implement or design"
            raise ValueError(msg)
        start_i = int(start_s)
        end_i = int(end_s)
        duration = max(0, end_i - start_i)
        # Issue #5504: a stall recovery can rerun the same round number in the same session
        # and timing ledger (e.g. the Step 5 review retry after aggregator-validation-exhausted).
        # Record an explicit 1-based attempt index in the reserved trailing column so the
        # progress report can split the Gantt per attempt instead of merging both attempts into
        # one window. Retries run strictly after the prior attempt returns, so counting prior
        # rows for this (skill, round) is race-free.
        attempt = self._next_round_attempt(skill=skill, round_n=int(round_n))
        row = [
            "v1", "round", str(int(time.time())), _san(skill), _san(step), str(int(round_n)), str(start_i),
            str(end_i), str(duration), str(int(accepted)), str(int(rejected)), (str(int(oos)) if oos is not None else "-"), str(attempt),
        ]
        self._append(row)

    def _next_round_attempt(self, *, skill: str, round_n: int) -> int:
        """1-based attempt index for the next round row of (skill, round_n).

        Counts existing ``v1 round`` rows for the same skill and round number already in the
        ledger. A stall recovery reruns a round sequentially in the same ledger (issue #5504),
        so each prior row is a prior attempt and ``count + 1`` is the new attempt's index. Rows
        written before the attempt column existed are still counted by ``(skill, round)``, so a
        pre-upgrade attempt is never lost.
        """
        if not self.path.is_file():
            return 1
        try:
            lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return 1
        skill_s = _san(skill)
        round_s = str(int(round_n))
        prior = 0
        for line in lines:
            cols = line.split("\t")
            if len(cols) == 13 and cols[0] == "v1" and cols[1] == "round" and cols[3] == skill_s and cols[5] == round_s:
                prior += 1
        return prior + 1

    def dump(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.is_file() else ""

    def _append(self, row: list[str]) -> None:
        _ensure_ledger(self.path)
        line = "\t".join(row) + "\n"
        try:
            import fcntl
        except ImportError:  # pragma: no cover
            with self.path.open("a", encoding="utf-8") as handle:
                _ = handle.write(line)
        else:
            deadline = time.monotonic() + TIMING_LOCK_TIMEOUT_S
            with self.path.open("a", encoding="utf-8") as handle:
                while True:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            print(f"timing: WARNING: flock lock acquisition failed; skipping append for {self.path}", file=sys.stderr)
                            return
                        time.sleep(0.05)
                try:
                    _ = handle.write(line)
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass


@dataclass(frozen=True)
class TimingReport:
    ledger_path: Path

    def render(
        self,
        *,
        mode: str = "full",
        fmt: str = "markdown",
        since_last_mark: bool = False,
        append_timing_section: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str:
        if since_last_mark:
            mode = "terse"
        data = self.render_json(mode="full", env=env)
        if mode == "summary":
            marks = _parse_rows(self.ledger_path)[0]
            if not marks:
                return "Timing report unavailable: no step marks in ledger"
            now = int((env or os.environ).get("LARCH_TEST_TIMING_NOW", str(int(time.time()))))
            first = marks[0]
            counts = _vendor_counts_since(path=self.ledger_path, start=first.ts, use_end=True)
            return f"Total: elapsed={_hms(now - first.ts)} vendor-tasks={sum(counts.values())} (codex={counts['codex']}, cursor={counts['cursor']}, claude={counts['claude']})"
        if mode == "terse":
            skill = (env or os.environ).get("LARCH_TIMING_SKILL", "implement")
            marks = [mark for mark in _parse_rows(self.ledger_path)[0] if mark.skill == skill]
            if not marks:
                return "Timing report unavailable: no step marks in ledger"
            last = marks[-1]
            now = int((env or os.environ).get("LARCH_TEST_TIMING_NOW", str(int(time.time()))))
            counts = _vendor_counts_since(path=self.ledger_path, start=last.ts, use_end=True)
            return f"{last.step}: elapsed={_hms(now - last.ts)} vendor-tasks={sum(counts.values())} (codex={counts['codex']}, cursor={counts['cursor']}, claude={counts['claude']})"
        if mode == "full" and not _parse_rows(self.ledger_path)[0]:
            return "Timing report unavailable: no step marks in ledger"
        if fmt not in {"json", "markdown"}:
            msg = f"unknown format: {fmt}"
            raise ValueError(msg)
        if fmt == "json":
            rendered = json.dumps(data, sort_keys=True)
        else:
            rendered = _render_markdown(data)
        if append_timing_section is not None:
            block = "<!-- timing-report-begin -->\n## Timing Report\n\n" + rendered + "\n<!-- timing-report-end -->\n"
            _replace_block(target=append_timing_section, block=block)
        return rendered

    def render_json(
        self,
        *,
        mode: str = "full",
        since_last_mark: bool = False,
        env: Mapping[str, str] | None = None,
    ) -> dict[str, object]:
        _ = mode, since_last_mark
        marks, vendors, rounds = _parse_rows(self.ledger_path)
        if not marks:
            return {}
        env_map = os.environ if env is None else env
        now = int(env_map.get("LARCH_TEST_TIMING_NOW", str(int(time.time()))))
        threshold = _positive_int(raw=env_map.get("LARCH_TIMING_OUTLIER_THRESHOLD_S"), default=14400)
        per_step: list[dict[str, object]] = []
        total_duration = 0
        implement_marks = [mark for mark in marks if mark.skill == "implement"]
        driving = implement_marks or marks
        if driving:
            total_duration = driving[-1].ts - driving[0].ts
        for idx, mark in enumerate(driving):
            end = driving[idx + 1].ts if idx + 1 < len(driving) else _last_event_ts(now=now, vendors=vendors)
            duration = max(0, end - mark.ts)
            row: dict[str, object] = {
                "skill": mark.skill,
                "step": mark.step,
                "duration_seconds": duration,
                "duration_hms": _hms(duration),
                "outlier": duration > threshold,
            }
            matched_rounds = _rounds_for(rounds=rounds, skill=mark.skill, step=mark.step, start=mark.ts, end=end)
            if matched_rounds:
                row["rounds"] = matched_rounds
            per_step.append(row)
            if mark.skill == "implement":
                for child in ("design", "review"):
                    for child_row in _child_steps(marks=marks, rounds=rounds, skill=child, start=mark.ts, end=end, now=now, threshold=threshold):
                        per_step.append(child_row)
        averages = _vendor_averages(vendors)
        return {
            "per_step": per_step,
            "total_seconds": max(0, total_duration),
            "total_hms": _hms(max(0, total_duration)),
            "vendor_task_averages": averages,
        }


@dataclass(frozen=True)
class _Mark:
    ts: int
    skill: str
    step: str


@dataclass(frozen=True)
class _Vendor:
    ts: int
    skill: str
    vendor: str
    task_kind: str
    start: int
    end: int
    duration: int
    output: str
    exit_code: int
    status: str


@dataclass(frozen=True)
class _Round:
    skill: str
    step: str
    round_n: int
    start: int
    end: int
    duration: int
    accepted: int
    rejected: int
    oos: int | None


def _under_allowed_root(*, path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    return any(resolved == base or base in resolved.parents for base in roots)


def validate_ledger_path(raw: str, *, must_exist: bool = False, env: Mapping[str, str] | None = None) -> Path:
    env_map = os.environ if env is None else env
    if not raw or ".." in Path(raw).parts:
        msg = f"ledger path must not be empty or contain '..': {raw}"
        raise ValueError(msg)
    roots = _allowed_roots(env=env_map)
    candidate = Path(raw)
    root = roots[0] if roots else Path("/tmp").resolve()
    if not candidate.is_absolute():
        candidate = root / candidate
    if not _under_allowed_root(path=candidate, roots=roots):
        msg = f"ledger path not under an allowed root: {raw}"
        raise ValueError(msg)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    parent = candidate.parent.resolve(strict=True)
    resolved = parent / candidate.name
    if not _under_allowed_root(path=resolved, roots=roots):
        msg = f"ledger path not under an allowed root: {raw}"
        raise ValueError(msg)
    if must_exist and not resolved.is_file():
        msg = f"ledger not found: {resolved}"
        raise ValueError(msg)
    if resolved.is_symlink():
        msg = f"ledger is a symlink: {resolved}"
        raise ValueError(msg)
    if resolved.exists() and not resolved.is_file():
        msg = f"ledger exists but is not a regular file: {resolved}"
        raise ValueError(msg)
    return resolved


def resolve_timing_ledger_path(*, ledger: str | None = None, env: Mapping[str, str] | None = None) -> Path | None:
    env_map = os.environ if env is None else env
    if ledger:
        return validate_ledger_path(ledger, env=env_map)
    if env_map.get("LARCH_TIMING_LEDGER"):
        try:
            return validate_ledger_path(str(env_map["LARCH_TIMING_LEDGER"]), env=env_map)
        except ValueError:
            pass
    for key in ("IMPLEMENT_TMPDIR", "SESSION_ENV_PATH", "DESIGN_TMPDIR", "REVIEW_TMPDIR"):
        raw = env_map.get(key, "")
        path = Path(raw).parent if key == "SESSION_ENV_PATH" and raw else Path(raw)
        if raw and path.is_dir():
            return path.resolve() / "timing-ledger.tsv"
    return None


def harness_mark(*, label: str, argv: list[str]) -> int:
    start = time.time()
    rc = 127
    try:
        proc = subprocess.run(argv, check=False)
        rc = proc.returncode
    except OSError as exc:
        print(f"timing harness-mark: {exc}", file=sys.stderr)
        if isinstance(exc, PermissionError):
            rc = 126
        elif isinstance(exc, FileNotFoundError):
            rc = 127
        else:
            rc = 1
    finally:
        elapsed = max(0.0, time.time() - start)
        print(f"LARCH_HARNESS_TIMING\t{label}\t{elapsed:.2f}s")
    return rc


def step_telemetry_mark(*, implement_tmpdir: Path, label: str) -> int:
    if not implement_tmpdir.is_absolute() or not implement_tmpdir.is_dir() or not label:
        return 0
    env = dict(os.environ)
    env["IMPLEMENT_TMPDIR"] = str(implement_tmpdir)
    sess = implement_tmpdir / "session-env.sh"
    for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
        value = _read_session_key(path=sess, key=key)
        if value:
            env[key] = value
    try:
        ledger = tokens.resolve_token_ledger_path(env=env)
        if ledger is not None:
            tokens.TokenLedger(ledger).mark(label)
    except Exception as exc:
        print(f"timing telemetry-mark: token mark skipped: {exc}", file=sys.stderr)
    try:
        tenv = dict(env)
        tenv["DESIGN_TMPDIR"] = ""
        tenv["LARCH_TIMING_SKILL"] = "implement"
        ledger = resolve_timing_ledger_path(env=tenv)
        if ledger is not None:
            TimingLedger(ledger, skill="implement").mark(label)
    except Exception as exc:
        print(f"timing telemetry-mark: timing mark skipped: {exc}", file=sys.stderr)
    return 0


def _read_session_key(*, path: Path, key: str) -> str:
    try:
        if not path.is_file():
            return ""
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == key:
                return value.strip().strip('"\'')
        return ""
    except Exception:
        return ""


def _allowed_roots(*, env: Mapping[str, str]) -> list[Path]:
    roots: list[Path] = []
    for raw in (env.get("TMPDIR") or "/tmp", "/private/tmp"):
        path = Path(raw)
        if path.is_dir():
            roots.append(path.resolve())
    for key in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "REVIEW_TMPDIR"):
        raw = env.get(key, "")
        if raw and Path(raw).is_dir():
            roots.append(Path(raw).resolve())
    sess = env.get("SESSION_ENV_PATH", "")
    if sess and Path(sess).parent.is_dir():
        roots.append(Path(sess).parent.resolve())
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _ensure_ledger(path: Path) -> None:
    if path.is_symlink():
        msg = f"ledger is a symlink, refusing to write: {path}"
        raise ValueError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.is_file():
        msg = f"ledger exists but is not a regular file: {path}"
        raise ValueError(msg)
    path.touch(mode=0o600, exist_ok=True)


def _san(value: str) -> str:
    return value.replace("\t", "<NUL>").replace("\n", "<NUL>").replace("\r", "<NUL>")


def _parse_rows(path: Path) -> tuple[list[_Mark], list[_Vendor], list[_Round]]:
    marks: list[_Mark] = []
    vendors: list[_Vendor] = []
    rounds: list[_Round] = []
    if not path.is_file():
        return marks, vendors, rounds
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) != 13 or parts[0] != "v1":
            print(f"timing report: WARNING: skipping malformed row with {len(parts)} columns", file=sys.stderr)
            continue
        if parts[1] == "mark":
            marks.append(_Mark(int(parts[2]), parts[3], parts[4]))
        elif parts[1] == "vendor":
            vendors.append(_Vendor(int(parts[2]), parts[3], parts[5], parts[6], int(parts[7]), int(parts[8]), int(parts[9]), parts[10], int(parts[11]), parts[12]))
        elif parts[1] == "round":
            oos = int(parts[11]) if parts[11].isdigit() else None
            rounds.append(_Round(parts[3], parts[4], int(parts[5]), int(parts[6]), int(parts[7]), int(parts[8]), int(parts[9]), int(parts[10]), oos))
    return marks, vendors, rounds


def _hms(seconds: float) -> str:
    sec = max(0, int(seconds))
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def _minutes(seconds: float) -> str:
    return f"{seconds / 60.0:.1f} min"


def _last_event_ts(*, now: int, vendors: list[_Vendor]) -> int:
    return max([now, *(vendor.ts for vendor in vendors)])


def _positive_int(*, raw: str | None, default: int) -> int:
    try:
        value = int(raw or "")
    except ValueError:
        return default
    return value if value > 0 else default




def _rounds_for(*, rounds: list[_Round], skill: str, step: str, start: int, end: int) -> list[dict[str, int]]:
    out: dict[int, _Round] = {}
    for row in rounds:
        if row.skill == skill and row.step == step and start <= row.start < end:
            out[row.round_n] = row
    result: list[dict[str, int]] = []
    for key in sorted(out):
        row = out[key]
        payload = {"round": row.round_n, "duration_seconds": row.duration, "accepted": row.accepted, "rejected": row.rejected}
        if skill == "design" and row.oos is not None:
            payload["oos"] = row.oos
        result.append(payload)
    return result


def _child_steps(*, marks: list[_Mark], rounds: list[_Round], skill: str, start: int, end: int, now: int, threshold: int) -> list[dict[str, object]]:
    skill_marks = [mark for mark in marks if mark.skill == skill]
    out: list[dict[str, object]] = []
    for idx, mark in enumerate(skill_marks):
        if not (start <= mark.ts < end):
            continue
        child_end = skill_marks[idx + 1].ts if idx + 1 < len(skill_marks) else now
        child_end = min(child_end, end)
        duration = max(0, child_end - mark.ts)
        payload: dict[str, object] = {"skill": skill, "step": mark.step, "duration_seconds": duration, "duration_hms": _hms(duration), "outlier": duration > threshold}
        matched = _rounds_for(rounds=rounds, skill=skill, step=mark.step, start=mark.ts, end=child_end)
        if matched:
            payload["rounds"] = matched
        out.append(payload)
    return out


def _vendor_averages(vendors: list[_Vendor]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], list[int]] = {}
    for row in vendors:
        if row.status == "complete" and row.exit_code == 0:
            buckets.setdefault((row.vendor, row.task_kind), []).append(row.duration)
    def order_key(item: tuple[tuple[str, str], list[int]]) -> tuple[int, str]:
        idx = {"codex": 1, "cursor": 2, "claude": 3}.get(item[0][0], 4)
        return idx, item[0][1]
    out: list[dict[str, object]] = []
    for (vendor, kind), values in sorted(buckets.items(), key=order_key):
        avg = sum(values) / len(values)
        out.append({
            "vendor": vendor,
            "task_kind": kind,
            "samples": len(values),
            "average_seconds": round(avg, 3),
            "average_hms": _hms(int(avg + 0.5)),
            "min_seconds": min(values),
            "max_seconds": max(values),
        })
    return out


def _vendor_counts_since(*, path: Path, start: int, use_end: bool = False) -> dict[str, int]:
    counts: dict[str, int] = {"codex": 0, "cursor": 0, "claude": 0}
    _, vendors, _ = _parse_rows(path)
    for row in vendors:
        compare = row.end if use_end else row.ts
        if compare >= start and row.vendor in counts:
            counts[row.vendor] += 1
    return counts


def _render_markdown(data: dict[str, object]) -> str:
    lines: list[str] = []
    lines.extend(["## Per-Step Durations", "", "| Skill | Step | Duration |", "| --- | --- | ---: |"])
    per_step_list: list[dict[str, Any]] = cast("list[dict[str, Any]]", data.get("per_step") or [])
    for r in per_step_list:
        step = str(r.get("step", "")).replace("|", "\\|")
        suffix = " [OUTLIER]" if r.get("outlier") else ""
        skill_val = str(r.get("skill") or "")
        hms_val = str(r.get("duration_hms") or "")
        lines.append(f"| {skill_val} | {step} | {hms_val}{suffix} |")
    lines.append(f"| **Total** | | {data.get('total_hms', '00:00:00')} |")
    lines.extend(["", "## Vendor Task Averages", "", "| Vendor | Task kind | Samples | Average | Range |", "| --- | --- | ---: | ---: | --- |"])
    vendor_avgs_list: list[dict[str, Any]] = cast("list[dict[str, Any]]", data.get("vendor_task_averages") or [])
    for r2 in vendor_avgs_list:
        samples = int(r2.get("samples") or 0)
        min_s = float(r2.get("min_seconds") or 0)
        max_s = float(r2.get("max_seconds") or 0)
        avg_s = float(r2.get("average_seconds") or 0)
        range_text = "(1 sample)" if samples == 1 else f"{_minutes(min_s)}-{_minutes(max_s)}"
        vendor_val = str(r2.get("vendor") or "")
        kind_val = str(r2.get("task_kind") or "")
        lines.append(f"| {vendor_val} | {kind_val} | {samples} | {_minutes(avg_s)} | {range_text} |")
    return "\n".join(lines)


def _marker_line_re(marker: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*<!-- {re.escape(marker)} -->\s*$")


def _replace_block(*, target: Path, block: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    begin_re = _marker_line_re("timing-report-begin")
    end_re = _marker_line_re("timing-report-end")
    lines = existing.splitlines(keepends=True)
    begin_idx: int | None = None
    end_idx: int | None = None
    has_begin = False
    has_end = False
    for idx, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        if begin_re.match(stripped):
            has_begin = True
            if begin_idx is None:
                begin_idx = idx
        if end_re.match(stripped):
            has_end = True
            if begin_idx is not None and end_idx is None:
                end_idx = idx
    if has_begin and has_end and begin_idx is not None and end_idx is not None:
        text = "".join(lines[:begin_idx]) + block + "".join(lines[end_idx + 1 :])
    elif has_begin and not has_end:
        print(
            f"timing report: warning: {target} has lone <!-- timing-report-begin --> marker; truncating from marker and rewriting block",
            file=sys.stderr,
        )
        kept: list[str] = []
        for line in lines:
            if begin_re.match(line.rstrip("\r\n")):
                break
            kept.append(line)
        text = "".join(kept)
        if text and not text.endswith("\n"):
            text += "\n"
        text += block
    elif has_end and not has_begin:
        print(
            f"timing report: warning: {target} has lone <!-- timing-report-end --> marker; dropping head through marker and rewriting block",
            file=sys.stderr,
        )
        kept_tail: list[str] = []
        past = False
        for line in lines:
            if end_re.match(line.rstrip("\r\n")):
                past = True
                continue
            if past:
                kept_tail.append(line)
        text = "".join(kept_tail)
        if text and not text.endswith("\n"):
            text += "\n"
        text += block
    else:
        text = existing + ("\n" if existing else "") + block
    tmp = target.with_name(target.name + ".tmp")
    _ = tmp.write_text(text, encoding="utf-8")
    _ = tmp.replace(target)


def _ledger_from_args(args: list[str]) -> tuple[list[str], str | None]:
    out: list[str] = []
    ledger: str | None = None
    idx = 0
    while idx < len(args):
        if args[idx] == "--ledger":
            ledger = args[idx + 1]
            idx += 2
        else:
            out.append(args[idx])
            idx += 1
    return out, ledger


def timing_mark_main(argv: list[str] | None = None) -> int:
    args, raw_ledger = _ledger_from_args(list(argv if argv is not None else sys.argv[1:]))
    if_latest_differs = "--if-latest-differs" in args
    if if_latest_differs:
        args = [a for a in args if a != "--if-latest-differs"]
    if not args:
        print("timing mark requires <step>", file=sys.stderr)
        return 1
    try:
        ledger = resolve_timing_ledger_path(ledger=raw_ledger)
    except ValueError as exc:
        print(f"timing mark: {exc}", file=sys.stderr)
        return 1
    if ledger is None:
        return 0
    if if_latest_differs:
        skill = os.environ.get("LARCH_TIMING_SKILL", "implement")
        skill_marks = [m for m in _parse_rows(ledger)[0] if m.skill == skill]
        if skill_marks and skill_marks[-1].step == args[0]:
            return 0
    try:
        TimingLedger(ledger, skill=os.environ.get("LARCH_TIMING_SKILL", "implement")).mark(args[0])
    except ValueError as exc:
        print(f"timing mark: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"timing mark: WARNING: ledger write skipped: {exc}", file=sys.stderr)
        return 0
    return 0


def timing_record_vendor_task_main(argv: list[str] | None = None) -> int:
    args, raw_ledger = _ledger_from_args(list(argv if argv is not None else sys.argv[1:]))
    opts = _flag_map(args)
    try:
        ledger = resolve_timing_ledger_path(ledger=raw_ledger)
    except ValueError as exc:
        print(f"timing record-vendor-task: {exc}", file=sys.stderr)
        return 1
    if ledger is None:
        return 0
    try:
        TimingLedger(ledger, skill=os.environ.get("LARCH_TIMING_SKILL", "implement")).record_vendor_task(
            vendor=opts["--vendor"],
            task_kind=opts["--task-kind"],
            start_s=float(opts["--start-s"]),
            end_s=float(opts["--end-s"]),
            output=opts["--output"],
            exit_code=int(opts.get("--exit-code", "0") or "0"),
            status=opts.get("--status", "complete") or "complete",
        )
    except (KeyError, ValueError) as exc:
        print(f"timing record-vendor-task: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"timing record-vendor-task: WARNING: ledger write skipped: {exc}", file=sys.stderr)
        return 0
    return 0


def timing_record_round_main(argv: list[str] | None = None) -> int:
    args, raw_ledger = _ledger_from_args(list(argv if argv is not None else sys.argv[1:]))
    opts = _flag_map(args)
    try:
        ledger = resolve_timing_ledger_path(ledger=raw_ledger)
    except ValueError as exc:
        print(f"timing record-round: {exc}", file=sys.stderr)
        return 1
    if ledger is None:
        return 0
    try:
        TimingLedger(ledger).record_round(
            skill=opts["--skill"], step=opts["--step"], round_n=int(opts["--round"]),
            start_s=float(opts["--start-s"]), end_s=float(opts["--end-s"]),
            accepted=int(opts["--accepted"]), rejected=int(opts["--rejected"]), oos=int(opts.get("--oos", "0") or "0"),
        )
    except (KeyError, ValueError) as exc:
        print(f"timing record-round: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"timing record-round: WARNING: ledger write skipped: {exc}", file=sys.stderr)
        return 0
    return 0


def timing_dump_main(argv: list[str] | None = None) -> int:
    _, raw_ledger = _ledger_from_args(list(argv if argv is not None else sys.argv[1:]))
    try:
        ledger = resolve_timing_ledger_path(ledger=raw_ledger)
    except ValueError as exc:
        print(f"timing dump: {exc}", file=sys.stderr)
        return 1
    if ledger is None:
        return 0
    print(ledger)
    if ledger.is_file() and ledger.stat().st_size > 0:
        _ = sys.stdout.write(ledger.read_text(encoding="utf-8"))
    return 0


def timing_report_main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    mode = ""
    fmt = "markdown"
    output: Path | None = None
    append: Path | None = None
    raw_ledger: str | None = None
    idx = 0
    try:
        while idx < len(args):
            arg = args[idx]
            if arg in ("--since-last-mark", "--terse"):
                mode = "terse"; idx += 1
            elif arg == "--summary":
                mode = "summary"; idx += 1
            elif arg == "--full":
                mode = "full"; idx += 1
            elif arg == "--markdown":
                fmt = "markdown"; idx += 1
            elif arg == "--format":
                fmt = args[idx + 1]; idx += 2
            elif arg == "--output":
                output = Path(args[idx + 1]); idx += 2
            elif arg == "--ledger":
                raw_ledger = args[idx + 1]; idx += 2
            elif arg == "--append-timing-section":
                append = Path(args[idx + 1]); mode = "full"; idx += 2
            else:
                raise ValueError(f"unknown flag: {arg}")
        if not mode:
            raise ValueError("missing report mode")
        if fmt not in {"json", "markdown"}:
            raise ValueError(f"unknown format: {fmt}")
        ledger = resolve_timing_ledger_path(ledger=raw_ledger)
        if ledger is None:
            raise ValueError("ledger path unavailable")
        rendered = TimingReport(ledger).render(mode=mode, fmt=fmt, append_timing_section=append)
        text = rendered + "\n"
        if mode == "full" and output is not None:
            tmp = output.with_name(output.name + ".tmp")
            _ = tmp.write_text(text, encoding="utf-8")
            _ = tmp.replace(output)
        elif append is None:
            _ = sys.stdout.write(text)
    except (IndexError, OSError, ValueError) as exc:
        print(f"Timing report unavailable: {exc}", file=sys.stderr)
        return 0
    return 0


def timing_harness_mark_main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if args[:1] == ["--label"]:
        if len(args) < 4 or args[2] != "--":
            print("timing harness-mark requires --label <label> -- <command> [args...]", file=sys.stderr)
            return 2
        return harness_mark(label=args[1], argv=args[3:])
    if len(args) >= 3 and args[1] == "--":
        return harness_mark(label=args[0], argv=args[2:])
    if len(args) < 2:
        print("timing harness-mark requires --label <label> -- <command> [args...]", file=sys.stderr)
        return 2
    return harness_mark(label=args[0], argv=args[1:])


def timing_telemetry_mark_main(argv: list[str] | None = None) -> int:
    opts = _flag_map(list(argv if argv is not None else sys.argv[1:]))
    raw = opts.get("--implement-tmpdir", "")
    if not raw:
        return 0
    implement_tmpdir = Path(raw)
    if not implement_tmpdir.is_absolute() or not implement_tmpdir.is_dir():
        return 0
    return step_telemetry_mark(implement_tmpdir=implement_tmpdir, label=opts.get("--label", ""))


def timing_task_kinds_main(argv: list[str] | None = None) -> int:
    _ = argv
    for kind in sorted(TIMING_TASK_KINDS_ALLOWED):
        print(kind)
    return 0


def _flag_map(args: list[str]) -> dict[str, str]:
    opts: dict[str, str] = {}
    idx = 0
    while idx < len(args):
        if args[idx].startswith("--") and idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            opts[args[idx]] = args[idx + 1]
            idx += 2
        elif args[idx].startswith("--"):
            opts[args[idx]] = ""
            idx += 1
        else:
            idx += 1
    return opts
