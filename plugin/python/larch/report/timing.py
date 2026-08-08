# ruff: noqa: PLC0415, SIM105, S108, PLR2004
# pylint: disable=all
"""Timing ledger writers still consumed in-process by Python runtime modules.

The `timing` commands moved to Rust in issue #8083. What remains here is the
library surface that Python callers still import directly: the ledger row
writers, the ledger path resolver, and the step-mark helper. No command is
registered from this module.
"""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping

# Canonical allow-list for literal --timing-task-kind values; update with every new literal call site.
# The Rust `timing task-kinds` owner publishes the same list to the allow-list lint.
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
    "codex-plan-autofix", "cursor-plan-autofix", "gate-b-apply", "voter-dispatch-prep",
    "reviewer-collect",
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
class TimingMarkResult:
    """Outcome of a timing step mark."""

    ledger_path: Path | None
    marked: bool


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
class _Mark:
    ts: int
    skill: str
    step: str


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


def mark(
    *,
    label: str,
    ledger: str | None = None,
    skill: str = "implement",
    if_latest_differs: bool = False,
    env: Mapping[str, str] | None = None,
) -> TimingMarkResult:
    """Record a timing mark, optionally suppressing a duplicate latest label."""
    path = resolve_timing_ledger_path(ledger=ledger, env=env)
    if path is None:
        return TimingMarkResult(ledger_path=None, marked=False)
    if if_latest_differs:
        skill_marks = [item for item in _parse_marks(path) if item.skill == skill]
        if skill_marks and skill_marks[-1].step == label:
            return TimingMarkResult(ledger_path=path, marked=False)
    TimingLedger(path, skill=skill).mark(label)
    return TimingMarkResult(ledger_path=path, marked=True)


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


def _parse_marks(path: Path) -> list[_Mark]:
    marks: list[_Mark] = []
    if not path.is_file():
        return marks
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) != 13 or parts[0] != "v1":
            print(f"timing report: WARNING: skipping malformed row with {len(parts)} columns", file=sys.stderr)
            continue
        if parts[1] == "mark":
            marks.append(_Mark(int(parts[2]), parts[3], parts[4]))
    return marks
