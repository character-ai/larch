"""Shared constants, data classes, and low-level I/O helpers for plan review."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.state.session_env import validate_design_tmpdir

_REPO_ROOT = Path(__file__).resolve().parents[3]
ROUND_CAP = 5
STRUCTURAL_DIFF_LINE_THRESHOLD = 500
STRUCTURAL_PLAN_LINE_THRESHOLD = 120
NON_NIT_CONTINUE_THRESHOLD = 5
STRUCTURAL_MIN_REVIEW_ROUNDS = 2
POSTPLAN_RC_PAUSE = 11
POSTPLAN_RC_PLAN_SIZE_WARN = 12
POSTPLAN_RC_OPERATOR = 32
MERGE_KEYS = (
    "TALLY_PLAN_REVIEW_STATUS",
    "IMPORTANT_ACCEPTED_COUNT",
    "AGGREGATOR_STATUS",
    "VOTING_TALLY_FILE",
    "PANEL_PRUNED_EMPTY",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
    "ROUND_NUM",
    "PLAN_REVIEW_CONTINUE_REASON",
    "REASON",
)
_STEP3_ROUND_CARRY_KEYS = ("DEGRADED_PANEL_WARNING", "INVALID_SLOT_PANEL_WARNING")
POSTPLAN_EMIT_KEYS = {
    "POSTPLAN_EMIT_STATUS",
    "EMIT_PLAN_STATUS",
    "DIFF_LINES",
    "VALIDATE_STATUS",
    "VALIDATE_DEFECT_COUNT",
    "PLAN_SIZE_STATUS",
    "SIZE_TRIGGER_FIRED",
    "TRIGGER_REASONS",
    "PLAN_LINES",
    "DIFF_ADDED",
    "DIFF_DELETED",
    "MECHANICAL_CHURN",
    "SOFT_ADVISORY",
    "PARTITION_REQUESTED",
    "DRIFT_TRIGGER_FIRED",
    "DRIFT_MULTIPLE",
    "DRIFT_PLAN_RATIO",
    "DRIFT_DIFF_RATIO",
    "BASELINE_PLAN_LINES",
    "BASELINE_DIFF_LINES",
}
OPTIONAL_TRAILER_KEYS = {"diff_added", "diff_deleted", "mechanical_churn"}


class PlanReviewError(RuntimeError):
    """Raised when native plan-review setup fails."""


@dataclass(frozen=True)
class AcceptedFinding:
    """Parsed accepted in-scope plan-review finding."""

    finding_id: int
    block: str
    severity_raw: str
    concern: str
    reviewers: str


@dataclass(frozen=True)
class GateBSeveritySummary:
    """Gate B severity mode, exclusive counts, display labels, and id order."""

    mode: str
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    display_labels: dict[int, str]
    finding_ids: tuple[int, ...]


@dataclass(frozen=True)
class GateBDisplayRow:
    """Rendered Gate B finding-row fields shared by preview and prompts."""

    finding_id: int
    display_severity_label: str
    reviewer_text: str
    excerpt: str


def _plugin_root() -> Path:
    return Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or _REPO_ROOT)


def _emit_kv(*, key: str, value: object = "") -> None:
    print(f"{key}={value}")


def _parse_kv_text(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _read_kv_file(path: Path) -> dict[str, str]:
    return larch_io.read_kvs(path, reject_symlink=True, default={})


def _strip_crlf(value: str) -> str:
    return value.replace("\r", "").replace("\n", "")


def _step3_round_carry_values(*, degraded_exit: bool, degraded_values: dict[str, str]) -> dict[str, str]:
    if degraded_exit:
        return dict(degraded_values)
    return {key: degraded_values[key] for key in _STEP3_ROUND_CARRY_KEYS if degraded_values.get(key)}


def _merge_step3_round_carry_warnings(*, values: dict[str, str], carry: dict[str, str]) -> dict[str, str]:
    merged = dict(values)
    for key in _STEP3_ROUND_CARRY_KEYS:
        if not merged.get(key) and carry.get(key):
            merged[key] = carry[key]
    return merged


def _write_atomic(*, path: Path, content: str) -> None:
    larch_io.atomic_write(path=path, text=content, create_parent=False, temp_name=f"{path.name}.tmp.{os.getpid()}")


def _validate_tmpdir_arg(design_tmpdir: str | Path) -> tuple[bool, str, Path]:
    raw = str(design_tmpdir)
    if not raw:
        return False, "DESIGN_TMPDIR required", Path(raw)
    path = Path(raw)
    if not path.is_dir():
        return False, "DESIGN_TMPDIR required", path
    ok, message = validate_design_tmpdir(raw)
    if not ok:
        return False, message, path
    if path.is_symlink():
        return False, "design-tmpdir must not be a symlink", path
    return True, "", path.resolve()


def _require_tmpdir(*, parser: argparse.ArgumentParser, design_tmpdir: str) -> Path:
    ok, message, path = _validate_tmpdir_arg(design_tmpdir)
    if not ok:
        parser.exit(2, f"{parser.prog}: {message}\n")
    return path


def _positive_int(value: str) -> int:
    if not value or not re.fullmatch(r"[0-9]+", value):
        raise argparse.ArgumentTypeError("requires a non-empty positive integer")
    number = int(value, 10)
    if number <= 0:
        raise argparse.ArgumentTypeError("requires a non-empty positive integer")
    return number


def _read_count(tmpdir: Path) -> int:
    raw = ""
    path = tmpdir / "review-round-count.txt"
    if path.is_file() and not path.is_symlink():
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    return int(raw, 10) if re.fullmatch(r"[0-9]+", raw) else 0


def _write_count(*, tmpdir: Path, count: int) -> None:
    _write_atomic(path=tmpdir / "review-round-count.txt", content=f"{count}\n")


def _count_accepted(tmpdir: Path) -> int:
    path = tmpdir / "accepted-plan-findings.md"
    if not path.is_file() or path.is_symlink():
        return 0
    return len(re.findall(r"(?m)^### FINDING_[0-9]+:", path.read_text(encoding="utf-8", errors="replace")))


def _run_command(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    capture: bool = True,
    stdin_text: str | None = None,
    cwd: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    run_cwd = str(cwd) if cwd is not None else str(_REPO_ROOT)
    return subprocess.run(argv, cwd=run_cwd, env=env, text=True, capture_output=capture, input=stdin_text, check=False)


# pyright: reportUnusedFunction=false
