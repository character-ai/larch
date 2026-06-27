"""Native entry points for /design Step 3 plan review."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.core import logging_util
from larch.review import plan_review_tally
from larch.review import plan_review_round
from larch.git.repo_roots import consumer_repo_root
from larch.design.design_lifecycle import (
    capture_contract_stream_to_paths,
    json_get_bool,
    json_get_bool_main as design_json_get_bool_main,
    _classify_input,  # pyright: ignore[reportPrivateUsage]
    _replay_warn_error,  # pyright: ignore[reportPrivateUsage]
    load_bash_quoted_env,
    phase_driver_read_result_env,
    phase_driver_write_result_env,
    read_result_env_main,
    stage_terminal_state_core,
)
from larch.state.session_env import validate_design_tmpdir
from larch.report.timing import TimingLedger

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


_STRUCTURED_GATE_B_SEVERITIES = {"blocking", "important", "latent", "nit"}
_GATE_B_LABELS_STRUCTURED = {
    "blocking": "High",
    "important": "High",
    "latent": "Medium",
    "nit": "Low",
}
_GATE_B_BUCKET_ORDER = ("Low", "Medium", "High", "Critical")


def _accepted_finding_field(block: str, *, label: str) -> str:
    pattern = re.compile(rf"(?mi)^-\s+(?:\*\*)?{re.escape(label)}(?:\*\*)?:\s*(.*)$")
    match = pattern.search(block)
    if not match:
        return ""
    lines = [match.group(1).strip()]
    tail = block[match.end() :].splitlines()
    for line in tail:
        if re.match(r"^(?:-\s+|###\s+)", line):
            break
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines).strip()


def _accepted_finding_reviewers(block: str) -> str:
    match = re.search(r"(?mi)^-\s+(?:\*\*)?Reviewer(?:\(s\))?(?:\*\*)?:\s*(.*)$", block)
    return match.group(1).strip() if match else ""


def _parse_accepted_findings(tmpdir: Path) -> list[AcceptedFinding]:
    path = tmpdir / "accepted-plan-findings.md"
    if not path.is_file() or path.is_symlink():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[AcceptedFinding] = []
    for block in re.findall(r"(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)", text):
        id_match = re.search(r"(?m)^### FINDING_([0-9]+):", block)
        if not id_match:
            continue
        severity_match = re.search(r"(?mi)^-\s+\*\*Severity\*\*:\s*([A-Za-z_-]+)\s*$", block)
        severity_raw = severity_match.group(1).lower() if severity_match else ""
        findings.append(
            AcceptedFinding(
                finding_id=int(id_match.group(1), 10),
                block=block,
                severity_raw=severity_raw,
                concern=_accepted_finding_field(block=block, label="Concern"),
                reviewers=_accepted_finding_reviewers(block),
            )
        )
    return findings


def _gate_b_fallback_predicates(concern: str) -> set[str]:
    text = concern.lower()
    matches: set[str] = set()
    if re.search(r"\b(style|naming|future[- ]proofing|no functional change)\b", text):
        matches.add("Low")
    if re.search(r"\b(robustness|clarity|secondary path|recoverable edge case)\b", text):
        matches.add("Medium")
    if re.search(
        r"\b(functional incorrectness|primary code path|missing required documentation contract|"
        r"missing required[^.]*doc|violates?[^.]*invariant|stated invariant)\b",
        text,
    ):
        matches.add("High")
    if re.search(
        r"\b(data loss|security breach|build/ci breakage|build breakage|ci breakage|"
        r"breaks (?:the )?build|breaks ci|downstream[^.]*regression|regression[^.]*downstream)\b",
        text,
    ):
        matches.add("Critical")
    return matches


def _gate_b_fallback_label(concern: str) -> str:
    # Gate B fallback mirrors skills/design/references/approval-gates.md:
    # collect every Concern-text predicate that matches, choose the lowest
    # bucket (Low < Medium < High < Critical), and default no-match or empty
    # concerns to Low. This display bucketing is intentionally separate from
    # plan_review_continuation's legacy whole-block high predicate.
    matches = _gate_b_fallback_predicates(concern)
    if not matches:
        return "Low"
    return min(matches, key=_GATE_B_BUCKET_ORDER.index)


def _classify_gate_b_severity(findings: Sequence[AcceptedFinding]) -> GateBSeveritySummary:
    structured = all(finding.severity_raw in _STRUCTURED_GATE_B_SEVERITIES for finding in findings)
    mode = "structured" if structured else "fallback"
    labels: dict[int, str] = {}
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for finding in findings:
        label = (
            _GATE_B_LABELS_STRUCTURED[finding.severity_raw]
            if structured
            else _gate_b_fallback_label(finding.concern)
        )
        labels[finding.finding_id] = label
        counts[label] += 1
    return GateBSeveritySummary(
        mode=mode,
        critical_count=counts["Critical"],
        high_count=counts["High"],
        medium_count=counts["Medium"],
        low_count=counts["Low"],
        display_labels=labels,
        finding_ids=tuple(finding.finding_id for finding in findings),
    )


def _gate_b_display_label(finding: AcceptedFinding, *, summary: GateBSeveritySummary) -> str:
    return summary.display_labels.get(finding.finding_id, "Low")


def _gate_b_excerpt(concern: str) -> str:
    lines = [line.strip() for line in concern.splitlines() if line.strip()][:2]
    return " ".join(lines)[:200]


def _gate_b_display_rows(tmpdir: Path) -> list[GateBDisplayRow]:
    findings = _parse_accepted_findings(tmpdir)
    summary = _classify_gate_b_severity(findings)
    return [
        GateBDisplayRow(
            finding_id=finding.finding_id,
            display_severity_label=_gate_b_display_label(finding=finding, summary=summary),
            reviewer_text=finding.reviewers,
            excerpt=_gate_b_excerpt(finding.concern),
        )
        for finding in findings
    ]


def _emit_gate_b_preview(tmpdir: Path) -> int:
    print("## Plan Review Findings — Review")
    print()
    for row in _gate_b_display_rows(tmpdir):
        print(f"FINDING_{row.finding_id} | {row.display_severity_label} | {row.reviewer_text} | {row.excerpt}")
    for name, header in (
        ("rejected-findings.md", "## Rejected Findings — Context"),
        ("oos.md", "## Out-of-Scope Findings — Context"),
    ):
        path = tmpdir / name
        text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() and not path.is_symlink() else ""
        if text.strip():
            print()
            print(header)
            print()
            print(text, end="" if text.endswith("\n") else "\n")
    return 0


def _write_phase(*, tmpdir: Path, round_num: int, phase: str) -> None:
    _write_atomic(path=tmpdir / f".step3-round-{round_num}.phase", content=f"{phase}\n")


def step3_loop_write_completed_step3(design_tmpdir: str | Path) -> None:
    completed = Path(design_tmpdir) / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-3").touch()
    (completed / "step-3.5").touch()


def step3_wrapper_write_completed_step3_only(design_tmpdir: str | Path) -> None:
    completed = Path(design_tmpdir) / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-3").touch()


def step3_loop_write_terminal_step3(design_tmpdir: str | Path) -> None:
    # #4688 terminal-sentinel contract: after the result env persists, write the
    # hook-release sentinel pair so hook-bg-poll-guard.sh releases the live
    # design-step3-review marker on the first <task-notification> and the
    # wrapper EXIT trap can guarantee step-3-terminal. Distinct from .completed/step-3
    # (the pause / Gate B milestone): mid-loop bail-outs write step-3-terminal
    # without step-3. Written on every terminal envelope persist, including the
    # apply-required / vote-required mid-loop bails.
    tmpdir = Path(design_tmpdir)
    completed = tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    terminal = completed / "step-3-terminal"
    sidecar = tmpdir / ".step3-terminal-persisted-this-run"
    for path in (terminal, sidecar):
        path.unlink(missing_ok=True)
    terminal.touch()
    sidecar.touch()


def _step3_normalize_write_terminal_sentinel(design_tmpdir: Path) -> None:
    # #5418 Fix A: write step-3-terminal ONLY (no sidecar) so the harness probe
    # returns success before KV output triggers a <task-notification>, without
    # engaging the EXIT trap's step-3 minting path (which requires the sidecar).
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    terminal = completed / "step-3-terminal"
    terminal.unlink(missing_ok=True)
    terminal.touch()


def step3_loop_status_to_loop_status(*, status: str, fallback: str = "complete") -> str:
    if status == "complete" and fallback == "zero-findings-degraded-panel":
        return fallback
    if status == "cap-hit":
        return "cap-reached"
    if status in {
        "complete",
        "main-agent-vote-required",
        "postplan-failed",
        "panel-failed",
        "panel-init-failed",
        "tally-error",
        "degraded-empty-collector",
    }:
        return status
    if status in {"main-agent-apply-required", "per-round-approval-required", "postplan-operator-required"}:
        return "complete"
    return fallback or "complete"



STEP3_NORMALIZE_ALLOW_KEYS = (
    "NEXT_ACTION",
    "LOOP_STATUS",
    "STEP3_REVIEW_LOOP_STATUS",
    "POSTPLAN_RC",
    "DEDUP_RC",
    "PLAN_REVIEW_CONTINUE_REASON",
    "FINAL_ROUND_NUM",
    "ACCEPTED_COUNT",
    "IMPORTANT_ACCEPTED_COUNT",
    "DEGRADED_PANEL",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
    "ROUNDS_COMPLETED",
    "TALLY_PLAN_REVIEW_STATUS",
    "AGGREGATOR_STATUS",
    "VOTING_TALLY_FILE",
    "SCOPE_ANCHOR_FILE",
    "STEP3_REVIEW_CAP_REACHED",
    "STEP3_REVIEW_ROUND_NUM",
    "ROUND_NUM",
    "REVIEW_ROUND_COUNT",
)
_STEP3_READ_RESULT_ENV_KEYS = (
    "NEXT_ACTION",
    "STEP3_REVIEW_LOOP_STATUS",
    "LOOP_STATUS",
    "ROUNDS_COMPLETED",
    "FINAL_ROUND_NUM",
    "ACCEPTED_COUNT",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
)
_STEP3_STATUS_VALUES = {
    "complete",
    "cap-hit",
    "main-agent-vote-required",
    "main-agent-apply-required",
    "per-round-approval-required",
    "postplan-operator-required",
    "postplan-failed",
    "panel-failed",
    "panel-init-failed",
    "tally-error",
    "degraded-empty-collector",
}
_STEP3_LOOP_STATUS_VALUES = {
    "complete",
    "cap-reached",
    "zero-findings-degraded-panel",
    "tally-error",
    "degraded-empty-collector",
    "panel-failed",
    "panel-init-failed",
    "main-agent-vote-required",
    "main-agent-apply-required",
    "per-round-approval-required",
    "postplan-operator-required",
    "postplan-failed",
}
_STEP3_EVIDENCE_STATUSES = {
    "panel-failed",
    "panel-init-failed",
    "tally-error",
    "degraded-empty-collector",
    "main-agent-vote-required",
    "main-agent-apply-required",
    "postplan-operator-required",
}
_STEP3_SYNTHESIS_STATUSES = {"panel-failed", "panel-init-failed", "tally-error", "degraded-empty-collector", "postplan-failed"}
# Statuses that require interactive main-agent action mid-loop; sentinel must NOT
# be written in normalize for these because the loop is not yet in a terminal state.
_STEP3_INTERACTIVE_STATUSES = {"main-agent-vote-required", "main-agent-apply-required", "per-round-approval-required", "postplan-operator-required"}
_STEP3_SUMMARY_FAILED_POSTPLAN = "SUMMARY_OUTCOME=failed-postplan"
_STEP3_SUMMARY_FAILED_JUDGE_PANEL = "SUMMARY_OUTCOME=failed-judge-panel"
_STEP3_NEXT_ACTION_BY_STATUS = {
    "complete": "step3b",
    "cap-hit": "step3b-bypass",
    "main-agent-vote-required": "mav",
    "main-agent-apply-required": "gate-b",
    "per-round-approval-required": "gate-b",
    "postplan-operator-required": "postplan-operator",
    "postplan-failed": "final-summary:failed-postplan",
    "panel-failed": "step3b-bypass",
    "panel-init-failed": "final-summary:failed-judge-panel",
    "tally-error": "step3b-bypass",
    "degraded-empty-collector": "step3b-bypass",
}


class _Step3NormalizeAbort(Exception):
    pass


def _step3_normalize_warn_stderr(message: str) -> None:
    print(message, file=sys.stderr)


def _step3_read_result_env_quiet(argv: Sequence[str]) -> tuple[int, Path | None, bool]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--input", dest="input_path")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--fallback-input", dest="fallback_input", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--allow", dest="allow", action="append", default=[])  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--output", dest="output_path")  # pyright: ignore[reportUnusedCallResult]
    try:
        ns, _extra = parser.parse_known_args(list(argv))
    except SystemExit:
        return 1, None, False
    primary = Path(ns.input_path or "")
    fallback = Path(ns.fallback_input) if ns.fallback_input else None
    primary_kind = _classify_input(primary)
    primary_regular = primary_kind == "regular"
    selected: Path | None = None
    if primary_regular:
        selected = primary
    elif fallback is not None and fallback.is_file() and not fallback.is_symlink():
        selected = fallback
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            rc = int(read_result_env_main(list(argv)))
        except SystemExit as exc:
            rc = int(exc.code) if isinstance(exc.code, int) else 1
    if rc == 0 and primary_regular and selected == primary and fallback is not None:
        try:
            primary_pairs = phase_driver_read_result_env(path=primary, allow_keys=ns.allow)
        except OSError:
            primary_pairs = []
        if not primary_pairs and fallback.is_file() and not fallback.is_symlink():
            selected = fallback
    if rc == 0:
        return 0, selected, primary_regular
    return rc, None, primary_regular


def _step3_replay_warn_error_safe(path: Path | None) -> None:
    if path is None or path.is_symlink() or not path.is_file():
        return
    try:
        _replay_warn_error(path)
    except OSError:
        return


def _step3_overlay_stdout_env(
    *,
    values: dict[str, str],
    stdout_file: Path,
    primary_regular: bool,
    selected_source: Path | None = None,
) -> None:
    if stdout_file.is_symlink() or not stdout_file.is_file():
        return
    allow = set(STEP3_NORMALIZE_ALLOW_KEYS)
    overlay_warn = primary_regular and selected_source != stdout_file
    try:
        lines = stdout_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in allow and value:
            values[key] = value
        elif key == "WARN" and overlay_warn:
            print(line)


def _step3_normalize_load_env(*, design_tmpdir: Path, stdout_file: Path) -> dict[str, str]:
    result_env = design_tmpdir / ".step3-review-result.env"
    values: dict[str, str] = {}
    safe_path: Path | None = None
    selected_source: Path | None = None
    primary_regular = _classify_input(result_env) == "regular"
    try:
        fd, safe_name = tempfile.mkstemp(prefix="larch-step3-review-env.", dir=os.environ.get("TMPDIR") or None)
        os.close(fd)
        safe_path = Path(safe_name)
    except OSError:
        _step3_normalize_warn_stderr(
            "**⚠ Step 3: could not allocate safe step3 review result env; aborting plan review**"
        )
        raise _Step3NormalizeAbort from None
    try:
        argv = ["--input", str(result_env), "--fallback-input", str(stdout_file)]
        for key in STEP3_NORMALIZE_ALLOW_KEYS:
            argv.extend(["--allow", key])
        argv.extend(["--output", str(safe_path)])
        rc, selected_source, primary_regular = _step3_read_result_env_quiet(argv)
        if rc == 0:
            values = load_bash_quoted_env(path=safe_path, allow_keys=STEP3_NORMALIZE_ALLOW_KEYS)
        else:
            _step3_normalize_warn_stderr(
                "**⚠ Step 3: could not read step3 review result env; recovering from plan-review stdout when possible**"
            )
            selected_source = stdout_file if stdout_file.is_file() and not stdout_file.is_symlink() else None
            primary_regular = _classify_input(result_env) == "regular"
    except OSError:
        _step3_normalize_warn_stderr(
            "**⚠ Step 3: could not read step3 review result env; recovering from plan-review stdout when possible**"
        )
        selected_source = stdout_file if stdout_file.is_file() and not stdout_file.is_symlink() else None
        primary_regular = _classify_input(result_env) == "regular"
    finally:
        with contextlib.suppress(FileNotFoundError):
            safe_path.unlink()
    _step3_replay_warn_error_safe(selected_source)
    _step3_overlay_stdout_env(
        values=values,
        stdout_file=stdout_file,
        primary_regular=primary_regular,
        selected_source=selected_source,
    )
    return values


def _step3_normalize_read_result_env(tmpdir: Path) -> int:
    result_env = tmpdir / ".step3-review-result.env"
    values = dict.fromkeys(_STEP3_READ_RESULT_ENV_KEYS, "")
    status = "missing"
    if result_env.is_file() and not result_env.is_symlink():
        status = "ok"
        try:
            for line in result_env.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key in values:
                    values[key] = value
        except OSError:
            status = "missing"
            values = dict.fromkeys(_STEP3_READ_RESULT_ENV_KEYS, "")
    if not values.get("NEXT_ACTION"):
        values["NEXT_ACTION"] = _step3_next_action(
            status=values.get("STEP3_REVIEW_LOOP_STATUS", ""),
            loop_status=values.get("LOOP_STATUS", ""),
        )
    _emit_kv(key="READ_RESULT_ENV_STATUS", value=status)
    for key in _STEP3_READ_RESULT_ENV_KEYS:
        _emit_kv(key=key, value=values[key])
    return 0


def _step3_back_map_loop_status(loop_status: str) -> str:
    return {
        "complete": "complete",
        "cap-reached": "cap-hit",
        "main-agent-vote-required": "main-agent-vote-required",
        "main-agent-apply-required": "main-agent-apply-required",
        "per-round-approval-required": "per-round-approval-required",
        "postplan-operator-required": "postplan-operator-required",
        "postplan-failed": "postplan-failed",
        "panel-failed": "panel-failed",
        "panel-init-failed": "panel-init-failed",
        "tally-error": "tally-error",
        "degraded-empty-collector": "degraded-empty-collector",
    }.get(loop_status, "")


def _step3_next_action(status: str, *, loop_status: str = "", tally_status: str = "") -> str:
    if loop_status == "zero-findings-degraded-panel":
        return "step3b"
    if tally_status == "tally-error" and (status == "complete" or loop_status == "complete"):
        return "step3b-bypass"
    if status:
        return _STEP3_NEXT_ACTION_BY_STATUS.get(status, "")
    return ""


def _step3_persist_next_action(tmpdir: Path, *, action: str) -> None:
    if not action:
        return
    result_env = tmpdir / ".step3-review-result.env"
    if result_env.is_symlink() or not result_env.is_file():
        return
    try:
        lines = result_env.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    preserved = [line for line in lines if not line.startswith("NEXT_ACTION=")]
    _write_atomic(path=result_env, content="NEXT_ACTION=" + action + "\n" + "\n".join(preserved) + ("\n" if preserved else ""))


def _step3_set_persist_next_action(tmpdir: Path, *, values: dict[str, str]) -> None:
    values["NEXT_ACTION"] = _step3_next_action(
        status=values.get("STEP3_REVIEW_LOOP_STATUS", ""),
        loop_status=values.get("LOOP_STATUS", ""),
        tally_status=values.get("TALLY_PLAN_REVIEW_STATUS", ""),
    )
    _step3_persist_next_action(tmpdir=tmpdir, action=values["NEXT_ACTION"])


def _step3_emit_normalize_envelope_with_next_action(tmpdir: Path, *, values: dict[str, str]) -> None:
    _step3_set_persist_next_action(tmpdir=tmpdir, values=values)
    _step3_emit_normalize_envelope(values)


def _step3_next_action_rows(*, action: str) -> list[tuple[str, str]]:
    return [("NEXT_ACTION", action)] if action else []


def _step3_emit_next_action(status: str, *, loop_status: str = "", tally_status: str = "") -> None:
    action = _step3_next_action(status=status, loop_status=loop_status, tally_status=tally_status)
    if action:
        _emit_kv(key="NEXT_ACTION", value=action)


def _step3_parse_rounds(values: dict[str, str]) -> int:
    raw = values.get("ROUNDS_COMPLETED") or values.get("REVIEW_ROUND_COUNT") or "0"
    return int(raw, 10) if re.fullmatch(r"[0-9]+", raw) else 0


def _step3_review_zero_round_coverage_missing(*, tmpdir: Path, rounds_completed: int) -> bool:
    if rounds_completed == 0:
        return True
    round_one = tmpdir / "plan-review" / "round-1"
    if not round_one.is_dir():
        return True
    try:
        return not any(child.is_file() and not child.is_symlink() for child in round_one.iterdir())
    except OSError:
        return True


def _step3_result_env_unusable(path: Path) -> bool:
    return path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK)


def _step3_review_write_result_env(*, tmpdir: Path, status: str, reason: str, rounds: int) -> None:
    result_env = tmpdir / ".step3-review-result.env"
    try:
        if result_env.is_symlink() or result_env.is_file():
            result_env.unlink()
        elif result_env.exists():
            return
        phase_driver_write_result_env(
            path=result_env,
            kvs=[
                ("NEXT_ACTION", _step3_next_action(status=status, loop_status=status)),
                ("STEP3_REVIEW_LOOP_STATUS", status),
                ("LOOP_STATUS", status),
                ("REASON", reason),
                ("TALLY_PLAN_REVIEW_STATUS", status),
                ("STEP3_REVIEW_CAP_REACHED", "false"),
                ("STEP3_REVIEW_ROUND_NUM", ""),
                ("ROUND_NUM", ""),
                ("ROUNDS_COMPLETED", str(rounds)),
                ("REVIEW_ROUND_COUNT", str(rounds)),
            ],
        )
        step3_loop_write_terminal_step3(tmpdir)
    except (OSError, ValueError):
        return


def _step3_emit_normalize_envelope(values: dict[str, str]) -> None:
    for key in (
        "NEXT_ACTION",
        "STEP3_REVIEW_LOOP_STATUS",
        "LOOP_STATUS",
        "POSTPLAN_RC",
        "DEDUP_RC",
        "FINAL_ROUND_NUM",
        "TALLY_PLAN_REVIEW_STATUS",
        "SCOPE_ANCHOR_FILE",
        "STEP3_REVIEW_ROUND_NUM",
        "ROUND_NUM",
        "REVIEW_ROUND_COUNT",
        "ROUNDS_COMPLETED",
        "ACCEPTED_COUNT",
        "IMPORTANT_ACCEPTED_COUNT",
        "STEP3_REVIEW_CAP_REACHED",
        "AGGREGATOR_STATUS",
        "VOTING_TALLY_FILE",
        "DEGRADED_PANEL",
        "DEGRADED_PANEL_WARNING",
        "INVALID_SLOT_PANEL_WARNING",
        "PLAN_REVIEW_CONTINUE_REASON",
    ):
        value = values.get(key, "")
        if value:
            _emit_kv(key=key, value=value)


def _step3_record_report_evidence_quiet(*, status: str, tmpdir: Path) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            return int(step3_record_report_evidence(status=status, design_tmpdir=tmpdir))
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 1


def normalize_step3_status_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review normalize-status")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--stdout-file", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--loop-rc", default="0")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--read-result-env", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv or []))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    if ns.read_result_env:
        return _step3_normalize_read_result_env(tmpdir)
    stdout_file = Path(ns.stdout_file)
    try:
        values = _step3_normalize_load_env(design_tmpdir=tmpdir, stdout_file=stdout_file)
    except _Step3NormalizeAbort:
        return 1
    if ns.loop_rc == "2":
        _step3_normalize_warn_stderr("**⚠ Step 3: plan-review run configuration error (exit 2); aborting plan review**")
        return 1

    step3_status = values.get("STEP3_REVIEW_LOOP_STATUS", "")
    loop_status = values.get("LOOP_STATUS", "")
    if not step3_status:
        step3_status = _step3_back_map_loop_status(loop_status)
        if step3_status:
            values["STEP3_REVIEW_LOOP_STATUS"] = step3_status
        if not step3_status and loop_status != "zero-findings-degraded-panel":
            _step3_normalize_warn_stderr("**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**")
            step3_status = "panel-failed"
            loop_status = "panel-failed"
            values["STEP3_REVIEW_LOOP_STATUS"] = step3_status
            values["LOOP_STATUS"] = loop_status
    if step3_status:
        if step3_status not in _STEP3_STATUS_VALUES:
            _step3_normalize_warn_stderr("**⚠ Step 3: missing or invalid STEP3_REVIEW_LOOP_STATUS after plan-review run; treating plan review as panel-failed**")
            step3_status = "panel-failed"
            values["STEP3_REVIEW_LOOP_STATUS"] = step3_status
        loop_status = step3_loop_status_to_loop_status(status=step3_status, fallback=values.get("LOOP_STATUS", "complete"))
        values["LOOP_STATUS"] = loop_status
    elif not loop_status or loop_status not in _STEP3_LOOP_STATUS_VALUES:
        _step3_normalize_warn_stderr("**⚠ Step 3: missing or invalid LOOP_STATUS after plan-review run; treating plan review as panel-failed**")
        loop_status = "panel-failed"
        values["LOOP_STATUS"] = loop_status

    rounds_completed = _step3_parse_rounds(values)
    if values.get("STEP3_REVIEW_LOOP_STATUS") == "panel-failed" and _step3_review_zero_round_coverage_missing(tmpdir=tmpdir, rounds_completed=rounds_completed):
        _step3_normalize_warn_stderr("**⚠ Step 3: panel failed before any reviewer round launched; treating as panel-init-failed**")
        values["STEP3_REVIEW_LOOP_STATUS"] = "panel-init-failed"
        values["LOOP_STATUS"] = "panel-init-failed"
        values["TALLY_PLAN_REVIEW_STATUS"] = "panel-init-failed"
        values["ROUNDS_COMPLETED"] = "0"
        values["REVIEW_ROUND_COUNT"] = "0"
        values["REASON"] = "panel-failed-zero-coverage"
        rounds_completed = 0
        _step3_review_write_result_env(tmpdir=tmpdir, status="panel-init-failed", reason="panel-failed-zero-coverage", rounds=0)

    status_for_synthesis = values.get("STEP3_REVIEW_LOOP_STATUS", "")
    result_env = tmpdir / ".step3-review-result.env"
    if status_for_synthesis in _STEP3_SYNTHESIS_STATUSES and _step3_result_env_unusable(result_env):
        _step3_normalize_warn_stderr(
            f"**⚠ Step 3: {status_for_synthesis} without a persisted result env; synthesizing terminal result env so the Step 3 completion sentinel is written**"
        )
        _step3_review_write_result_env(tmpdir=tmpdir, status=status_for_synthesis, reason=values.get("REASON", "result-env-missing-after-loop"), rounds=rounds_completed)

    # #5418 Fix A: write step-3-terminal before emitting KV output so that the
    # harness probe triggered by the <task-notification> finds the sentinel
    # present. Write only the sentinel (not the sidecar) so the wrapper EXIT
    # trap's step-3 minting gate remains intact. Guard: skip interactive
    # mid-loop statuses (mav/gate-b) that are not terminal.
    _step3_normalize_terminal_status = values.get("STEP3_REVIEW_LOOP_STATUS", "")
    if _step3_normalize_terminal_status and _step3_normalize_terminal_status not in _STEP3_INTERACTIVE_STATUSES:
        _step3_normalize_write_terminal_sentinel(tmpdir)
    _step3_emit_normalize_envelope_with_next_action(tmpdir=tmpdir, values=values)

    status = values.get("STEP3_REVIEW_LOOP_STATUS", "")
    if status in _STEP3_EVIDENCE_STATUSES and _step3_record_report_evidence_quiet(status=status, tmpdir=tmpdir) != 0:
        _step3_normalize_warn_stderr(f"**⚠ Step 3: failed to record escalation evidence for {status}**")
    if status == "postplan-failed":
        print(_STEP3_SUMMARY_FAILED_POSTPLAN)
        return 1
    if status == "panel-init-failed":
        print(_STEP3_SUMMARY_FAILED_JUDGE_PANEL)
        return 1
    return 0


def step3_stage_postplan_failed(*, design_tmpdir: str | Path, postplan_rc: str = "unknown") -> int:
    tmpdir = Path(design_tmpdir)
    sentinel = tmpdir / ".step3-postplan-terminal-state.recorded"
    if sentinel.exists() or sentinel.is_symlink():
        return 0
    stdout = tmpdir / "step3-stage-terminal-state.stdout.log"
    stderr = tmpdir / "step3-stage-terminal-state.stderr.log"
    rc = capture_contract_stream_to_paths(
        stage_terminal_state_core,
        stdout,
        stderr,
        [
            "--design-tmpdir",
            str(tmpdir),
            "--outcome",
            "failed-postplan",
            "--step",
            "postplan",
            "--phase",
            "postplan",
            "--site",
            "step3-review",
            "--trigger",
            "postplan-failed",
            "--bail-reason",
            "postplan-failed",
            "--exit-code",
            postplan_rc,
            "--source-script",
            "design-step3-review",
            "--summary-outcome",
            "failed-postplan",
        ],
    )
    if rc == 0:
        sentinel.touch()
        return 0
    logging_util.emit_kv(key="WARN", value="Step 3: failed to stage failed-postplan terminal state")
    return 1


def stage_panel_init_failed(*, design_tmpdir: str | Path, trigger: str = "panel-init-failed") -> int:
    tmpdir = Path(design_tmpdir)
    sentinel = tmpdir / ".step3-panel-init-terminal-state.recorded"
    if sentinel.exists() or sentinel.is_symlink():
        return 0
    stdout = tmpdir / "step3-panel-init-terminal-state.stdout.log"
    stderr = tmpdir / "step3-panel-init-terminal-state.stderr.log"
    rc = capture_contract_stream_to_paths(
        stage_terminal_state_core,
        stdout,
        stderr,
        [
            "--design-tmpdir",
            str(tmpdir),
            "--outcome",
            "failed-judge-panel",
            "--step",
            "step3",
            "--phase",
            "validation",
            "--site",
            "step3-review",
            "--trigger",
            trigger,
            "--bail-reason",
            trigger,
            "--exit-code",
            "1",
            "--source-script",
            "design-step3-review",
            "--summary-outcome",
            "failed-judge-panel",
        ],
    )
    if rc == 0:
        sentinel.touch()
        return 0
    logging_util.emit_kv(key="WARN", value="Step 3: failed to stage panel-init-failed terminal state")
    return 1


def step3_record_report_evidence(
    *,
    status: str,
    design_tmpdir: str | Path | None = None,
    cli_surface: bool = False,
) -> int:
    if cli_surface and design_tmpdir is None:
        print("plan-review run: --design-tmpdir is required with --record-report-evidence", file=sys.stderr)
        return 2
    tmpdir_raw = str(design_tmpdir or os.environ.get("DESIGN_TMPDIR", ""))
    if not tmpdir_raw:
        return 0
    ok, message, tmpdir = _validate_tmpdir_arg(tmpdir_raw)
    if not ok:
        if cli_surface:
            print(f"plan-review run: {message}", file=sys.stderr)
        return 2
    phase = {
        "main-agent-vote-required": "validation",
        "main-agent-apply-required": "validation",
        "postplan-operator-required": "postplan",
        "panel-failed": "validation",
        "panel-init-failed": "validation",
        "tally-error": "validation",
        "degraded-empty-collector": "validation",
    }.get(status)
    if phase is None:
        return 0
    sentinel = tmpdir / f".step3-report-{status}.recorded"
    if sentinel.exists() or sentinel.is_symlink():
        return 0
    helper_cmd = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "stall-recovery"]
    stdout = tmpdir / f"step3-record-escalation-{status}.stdout.log"
    stderr = tmpdir / f"step3-record-escalation-{status}.stderr.log"
    try:
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            proc = subprocess.run(
                [
                    *helper_cmd,
                    "record-escalation",
                    "--profile",
                    "generic",
                    "--artifact-prefix",
                    "design-failure",
                    "--implement-tmpdir",
                    str(tmpdir),
                    "--site",
                    "step3-review",
                    "--trigger",
                    status,
                    "--step",
                    "step3",
                    "--phase",
                    phase,
                    "--dispatcher",
                    "design-step3-review",
                ],
                cwd=str(_REPO_ROOT),
                stdout=out,
                stderr=err,
                check=False,
            )
        if proc.returncode == 0:
            sentinel.touch()
            return 0
    except OSError:
        pass
    logging_util.emit_kv(key="WARN", value=f"Step 3: failed to record design escalation evidence for {status}")
    return 1


def step3_loop_persist_envelope(
    *,
    design_tmpdir: str | Path,
    status: str,
    round_num: int,
    rounds_completed: int,
    final_round: int,
    values: dict[str, str] | None = None,
) -> None:
    tmpdir = Path(design_tmpdir)
    vals = dict(values or {})
    loop_status = step3_loop_status_to_loop_status(status=status, fallback=vals.get("LOOP_STATUS", "complete"))
    if status == "cap-hit":
        persist_round_num = ""
        persist_review_count = str(rounds_completed)
    elif status in {"tally-error", "degraded-empty-collector", "panel-failed", "postplan-failed"}:
        persist_round_num = ""
        persist_review_count = str(_read_count(tmpdir))
    else:
        persist_round_num = str(round_num) if round_num else ""
        persist_review_count = str(round_num or 0)
    safe_reason = _strip_crlf(vals.get("PLAN_REVIEW_CONTINUE_REASON", os.environ.get("PLAN_REVIEW_CONTINUE_REASON", "")))
    safe_scope = vals.get("SCOPE_ANCHOR_FILE", os.environ.get("SCOPE_ANCHOR_FILE", ""))
    if "\n" in safe_scope or "\r" in safe_scope:
        safe_scope = ""
    next_action = _step3_next_action(status=status, loop_status=loop_status, tally_status=vals.get("TALLY_PLAN_REVIEW_STATUS", ""))
    rows = _step3_next_action_rows(action=next_action)
    if loop_status != "zero-findings-degraded-panel":
        rows.append(("STEP3_REVIEW_LOOP_STATUS", status))
    rows.extend(
        [
        ("LOOP_STATUS", loop_status),
        ("FINAL_ROUND_NUM", str(final_round or round_num)),
        ("ROUNDS_COMPLETED", str(rounds_completed or 0)),
        ("ACCEPTED_COUNT", vals.get("ACCEPTED_COUNT", "0")),
        ("IMPORTANT_ACCEPTED_COUNT", vals.get("IMPORTANT_ACCEPTED_COUNT", "0")),
        ("DEGRADED_PANEL", vals.get("DEGRADED_PANEL", "0")),
        ("STEP3_REVIEW_ROUND_NUM", persist_round_num),
        ("REVIEW_ROUND_COUNT", persist_review_count),
        ("ROUND_NUM", vals.get("ROUND_NUM", str(round_num))),
        ("TALLY_PLAN_REVIEW_STATUS", vals.get("TALLY_PLAN_REVIEW_STATUS", "")),
        ("AGGREGATOR_STATUS", vals.get("AGGREGATOR_STATUS", "")),
        ("VOTING_TALLY_FILE", vals.get("VOTING_TALLY_FILE", "")),
        ("PANEL_PRUNED_EMPTY", vals.get("PANEL_PRUNED_EMPTY", "false")),
        ("REASON", vals.get("REASON", "")),
        ]
    )
    rows.extend((opt, vals[opt]) for opt in ("POSTPLAN_RC", "DEDUP_RC") if vals.get(opt))
    if vals.get("DEGRADED_PANEL_WARNING"):
        rows.append(("DEGRADED_PANEL_WARNING", _strip_crlf(vals["DEGRADED_PANEL_WARNING"])))
    if vals.get("INVALID_SLOT_PANEL_WARNING"):
        rows.append(("INVALID_SLOT_PANEL_WARNING", _strip_crlf(vals["INVALID_SLOT_PANEL_WARNING"])))
    if safe_reason:
        rows.append(("PLAN_REVIEW_CONTINUE_REASON", safe_reason))
    if safe_scope:
        rows.append(("SCOPE_ANCHOR_FILE", safe_scope))
    result_env = tmpdir / ".step3-review-result.env"
    existing = _read_kv_file(path=result_env)
    present = {key for key, value in rows if value}
    for key in MERGE_KEYS:
        value = existing.get(key, "")
        if key in present or not value:
            continue
        if key == "PLAN_REVIEW_CONTINUE_REASON":
            value = _strip_crlf(value)
            if not value:
                continue
        rows.append((key, value))
    phase_driver_write_result_env(path=result_env, kvs=rows)
    step3_loop_write_terminal_step3(tmpdir)


def step3_loop_emit_envelope(*, tmpdir: Path, status: str, round_num: int, rounds_completed: int, final_round: int, values: dict[str, str]) -> None:
    loop_status = values.get("LOOP_STATUS", "")
    if status == "postplan-failed":
        _ = step3_stage_postplan_failed(design_tmpdir=tmpdir, postplan_rc=values.get("POSTPLAN_RC", "unknown"))
    else:
        _ = step3_record_report_evidence(status=status, design_tmpdir=tmpdir)
    reason = _strip_crlf(values.get("PLAN_REVIEW_CONTINUE_REASON", ""))
    scope_anchor = values.get("SCOPE_ANCHOR_FILE", "")
    _step3_emit_next_action(status=status, loop_status=loop_status, tally_status=values.get("TALLY_PLAN_REVIEW_STATUS", ""))
    if loop_status != "zero-findings-degraded-panel":
        _emit_kv(key="STEP3_REVIEW_LOOP_STATUS", value=status)
    _emit_kv(key="ROUNDS_COMPLETED", value=rounds_completed)
    _emit_kv(key="FINAL_ROUND_NUM", value=final_round or round_num)
    _emit_kv(key="ACCEPTED_COUNT", value=values.get("ACCEPTED_COUNT", "0"))
    _emit_kv(key="DEGRADED_PANEL", value=values.get("DEGRADED_PANEL", "0"))
    if values.get("DEGRADED_PANEL_WARNING"):
        _emit_kv(key="DEGRADED_PANEL_WARNING", value=_strip_crlf(values["DEGRADED_PANEL_WARNING"]))
    if values.get("INVALID_SLOT_PANEL_WARNING"):
        _emit_kv(key="INVALID_SLOT_PANEL_WARNING", value=_strip_crlf(values["INVALID_SLOT_PANEL_WARNING"]))
    if scope_anchor and "\n" not in scope_anchor and "\r" not in scope_anchor:
        _emit_kv(key="SCOPE_ANCHOR_FILE", value=scope_anchor)
    _emit_kv(key="PLAN_REVIEW_CONTINUE_REASON", value=reason)
    _emit_kv(key="REASON", value=values.get("REASON", ""))
    for opt in ("POSTPLAN_RC", "DEDUP_RC"):
        if values.get(opt):
            _emit_kv(key=opt, value=values[opt])
    postplan_env = _read_kv_file(path=tmpdir / ".design-postplan-emit-result.env")
    for key, value in postplan_env.items():
        if key in POSTPLAN_EMIT_KEYS:
            _emit_kv(key=key, value=value)
    step3_loop_persist_envelope(design_tmpdir=tmpdir, status=status, round_num=round_num, rounds_completed=rounds_completed, final_round=final_round, values=values)


def emit_plan(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review emit")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    plan = tmpdir / "plan.txt"
    text = plan.read_text(encoding="utf-8", errors="replace") if plan.is_file() and not plan.is_symlink() else ""
    match = re.search(r"(?mi)^diff_lines:\s*([0-9]+)\s*$", text)
    if not match:
        _emit_kv(key="EMIT_PLAN_STATUS", value="missing-diff-lines")
        return 1
    _write_atomic(path=tmpdir / "diff-lines.txt", content=f"{match.group(1)}\n")
    _emit_kv(key="EMIT_PLAN_STATUS", value="ok")
    _emit_kv(key="DIFF_LINES", value=match.group(1))
    return 0


def finalize_plan(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review finalize")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    for name in ("voting-tally.md", "accepted-plan-findings.md", "rejected-findings.md", "oos.md"):
        path = tmpdir / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            _emit_kv(key="FINALIZE_PLAN_STATUS", value="invalid-artifact")
            return 1
    for name, content in {
        "voting-tally.md": "## Plan Review Tally\n\n",
        "accepted-plan-findings.md": "",
        "rejected-findings.md": "",
        "oos.md": "",
    }.items():
        path = tmpdir / name
        if not path.exists():
            _write_atomic(path=path, content=content)
    _emit_kv(key="FINALIZE_PLAN_STATUS", value="ok")
    return 0


def _parse_preview_args(argv: Sequence[str]) -> tuple[str, str]:
    design_tmpdir = ""
    variant = "step3"
    args = list(argv)
    idx = 0
    while idx < len(args):
        if args[idx] == "--design-tmpdir" and idx + 1 < len(args):
            design_tmpdir = args[idx + 1]
            idx += 2
        elif args[idx] == "--variant" and idx + 1 < len(args):
            variant = args[idx + 1]
            idx += 2
        else:
            idx += 1
    return design_tmpdir, variant


def emit_design_plan_preview(argv: Sequence[str]) -> int:
    """Step 3 plan-candidate preview and Gate C final-plan preview."""
    design_tmpdir, variant = _parse_preview_args(argv)
    missing_messages = {
        "step2b": "**⚠ 2b:** DESIGN_TMPDIR missing or invalid; cannot present implementation plan",
        "step3": "**⚠ 3: DESIGN_TMPDIR missing or invalid; cannot present plan candidate for review**",
        "gate-b": "**⚠ 3.5: DESIGN_TMPDIR missing or invalid; cannot present Gate B findings review**",
        "gatec": "**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**",
        "full": "**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**",
    }
    allowlist_messages = {
        "step2b": "**⚠ 2b:** DESIGN_TMPDIR not under allowlist; cannot present implementation plan",
        "step3": "**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**",
        "gate-b": "**⚠ 3.5: DESIGN_TMPDIR not under allowlist; cannot present Gate B findings review**",
        "gatec": "**⚠ 4b: DESIGN_TMPDIR not under allowlist; cannot present final design plan**",
        "full": "**⚠ 4b: DESIGN_TMPDIR not under allowlist; cannot present final design plan**",
    }
    ok, message, tmpdir = _validate_tmpdir_arg(design_tmpdir)
    if not ok:
        if "allowlist" in message:
            print(allowlist_messages.get(variant, allowlist_messages["step3"]))
        else:
            print(missing_messages.get(variant, missing_messages["step3"]))
        return 0
    if variant == "gate-b":
        return _emit_gate_b_preview(tmpdir)
    plan = tmpdir / "plan.txt"
    text = plan.read_text(encoding="utf-8", errors="replace") if plan.is_file() and not plan.is_symlink() else ""
    threshold_raw = os.environ.get("LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD", "120")
    threshold = int(threshold_raw) if re.fullmatch(r"[0-9]+", threshold_raw) else 120
    if variant == "full":
        script_override = os.environ.get("EMIT_DESIGN_PLAN_PREVIEW_SH", "")
        script_default = str(_plugin_root() / "skills" / "design" / "scripts" / "emit-design-plan-preview.sh")
        script = script_override or script_default
        if Path(script).is_file() and os.access(script, os.X_OK):
            proc = subprocess.run(
                [script, "--design-tmpdir", str(tmpdir), "--variant", "full"],
                cwd=str(_REPO_ROOT),
                check=False,
            )
            return proc.returncode
    if variant in {"gatec", "full"}:
        print("## Final Design Plan")
    elif variant == "step2b":
        print("## Implementation Plan")
    else:
        print("## Plan Candidate for Review")
        (tmpdir / ".step3-entry-plan-printed").touch()
    print()
    if len(text.splitlines()) > threshold:
        print("The plan is very large. Showing the full plan body below.")
        print()
    print(text, end="" if text.endswith("\n") or not text else "\n")
    return 0


def gate_b_counts(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review gate-b-counts")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    findings = _parse_accepted_findings(tmpdir)
    summary = _classify_gate_b_severity(findings)
    _emit_kv(key="ACCEPTED_COUNT", value=len(findings))
    _emit_kv(key="HIGH_ACCEPTED_COUNT", value=summary.high_count)
    _emit_kv(key="MEDIUM_ACCEPTED_COUNT", value=summary.medium_count)
    _emit_kv(key="LOW_ACCEPTED_COUNT", value=summary.low_count)
    _emit_kv(key="CRITICAL_ACCEPTED_COUNT", value=summary.critical_count)
    _emit_kv(key="GATE_B_SEVERITY_MODE", value=summary.mode)
    _emit_kv(key="FINDING_IDS", value=",".join(str(finding_id) for finding_id in summary.finding_ids))
    return 0


def _gate_b_prompt_line(row: GateBDisplayRow) -> str:
    prefix = f"FINDING_{row.finding_id} [{row.display_severity_label}]"
    if row.reviewer_text and row.excerpt:
        detail = f"{row.reviewer_text}: {row.excerpt}"
    elif row.reviewer_text:
        detail = row.reviewer_text
    else:
        detail = row.excerpt
    if detail:
        return f"{prefix} — {detail}. Apply this finding to the plan?"
    return f"{prefix} — Apply this finding to the plan?"


def gate_b_finding_line(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review gate-b-finding-line")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--finding-id", type=_positive_int, required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--ordinal", type=_positive_int)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    rows = _gate_b_display_rows(tmpdir)
    ids = [row.finding_id for row in rows]
    if ns.finding_id not in ids:
        parser.exit(1, f"{parser.prog}: unknown finding id FINDING_{ns.finding_id}\n")
    row = rows[ids.index(ns.finding_id)]
    if ns.ordinal is None:
        ordinal = ids.index(ns.finding_id) + 1
    else:
        ordinal = ns.ordinal
        if ordinal > len(ids) or ids[ordinal - 1] != ns.finding_id:
            parser.exit(1, f"{parser.prog}: ordinal does not match FINDING_{ns.finding_id}\n")
    total = len(ids)
    _emit_kv(key="FINDING_ID", value=row.finding_id)
    _emit_kv(key="DISPLAY_SEVERITY", value=row.display_severity_label)
    _emit_kv(key="REVIEWER_TEXT", value=row.reviewer_text)
    _emit_kv(key="CONCERN_EXCERPT", value=row.excerpt)
    _emit_kv(key="ONE_BY_ONE_ORDINAL", value=ordinal)
    _emit_kv(key="ONE_BY_ONE_TOTAL", value=total)
    _emit_kv(key="ONE_BY_ONE_HEADER", value=f"Finding {ordinal}/{total}")
    _emit_kv(key="ONE_BY_ONE_PROMPT_LINE", value=_gate_b_prompt_line(row))
    return 0


def _trailer_map(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([a-z_]+):\s*(.*?)\s*$", line)
        if match and match.group(1) in OPTIONAL_TRAILER_KEYS:
            values[match.group(1)] = match.group(2)
    return values


def gate_b_dedup_plan(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review gate-b-dedup")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--snapshot-trailers", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--dedup", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    plan = tmpdir / "plan.txt"
    text = plan.read_text(encoding="utf-8", errors="replace") if plan.is_file() and not plan.is_symlink() else ""
    keys_file = tmpdir / ".gate-b-optional-trailer-keys"
    values_file = tmpdir / ".gate-b-optional-trailer-keys.values"
    if ns.snapshot_trailers:
        trailers = _trailer_map(text)
        _write_atomic(path=keys_file, content="".join(f"{key}\n" for key in sorted(trailers)))
        _write_atomic(path=values_file, content="".join(f"{key}={trailers[key]}\n" for key in sorted(trailers)))
        _emit_kv(key="GATE_B_DEDUP_STATUS", value="snapshot-ok")
        return 0
    if not ns.dedup:
        parser.error("one of --snapshot-trailers or --dedup is required")
    if not keys_file.is_file() or keys_file.is_symlink() or not values_file.is_file() or values_file.is_symlink():
        _emit_kv(key="GATE_B_DEDUP_STATUS", value="missing-snapshot")
        return 3
    snapshot_keys = {line.strip() for line in keys_file.read_text(encoding="utf-8").splitlines() if line.strip()}
    current = _trailer_map(text)
    if not set(current).issubset(snapshot_keys) or not snapshot_keys.issubset(set(current)):
        _emit_kv(key="GATE_B_DEDUP_STATUS", value="trailer-key-drift")
        return 1
    seen: set[str] = set()
    removed = 0
    out_lines: list[str] = []
    for line in text.splitlines():
        if re.match(r"^[a-z_]+:\s*", line):
            out_lines.append(line)
            continue
        if line and line in seen:
            removed += 1
            continue
        if line:
            seen.add(line)
        out_lines.append(line)
    _write_atomic(path=plan, content="\n".join(out_lines) + ("\n" if text.endswith("\n") else ""))
    print(f"dedup-sweep: removed {removed} duplicate line(s) from plan.txt")
    _emit_kv(key="GATE_B_DEDUP_STATUS", value="ok")
    return 0


def persist_retally_step3_env(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review persist-retally-env")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--retally-stdout-file", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--retally-input-anchor", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--tally-plan-review-status", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--loop-status", required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    retally = _read_kv_file(path=Path(ns.retally_stdout_file))
    status = ns.tally_plan_review_status
    # Preserve round-count fields from the existing primary result env so that
    # callers like resolve_artifact_round remain stable across idempotent re-runs.
    existing = _read_kv_file(path=tmpdir / ".step3-plan-review-result.env")
    rows: list[tuple[str, str]] = [
        ("TALLY_PLAN_REVIEW_STATUS", status),
        ("LOOP_STATUS", ns.loop_status),
        ("VOTING_TALLY_FILE", retally.get("VOTING_TALLY_FILE", "")),
    ]
    if status == "tally-error":
        rows.insert(0, ("NEXT_ACTION", "step3b-bypass"))
    for carry_key in ("ROUNDS_COMPLETED", "FINAL_ROUND_NUM", "STEP3_REVIEW_ROUND_NUM"):
        val = existing.get(carry_key, "")
        if val and re.fullmatch(r"[0-9]+", val):
            rows.append((carry_key, val))
    if status == "tally-error":
        for name in ("accepted-plan-findings.md", "rejected-findings.md", "oos.md"):
            _write_atomic(path=tmpdir / name, content="")
        rows.extend([("ACCEPTED_COUNT", "0"), ("IMPORTANT_ACCEPTED_COUNT", "0")])
    else:
        rows.extend([
            ("ACCEPTED_COUNT", retally.get("ACCEPTED_COUNT", "0")),
            ("IMPORTANT_ACCEPTED_COUNT", retally.get("IMPORTANT_ACCEPTED_COUNT", "0")),
        ])
        scope = retally.get("SCOPE_ANCHOR_FILE", "")
        if scope and "\n" not in scope and "\r" not in scope:
            scope_path = Path(scope)
            if scope_path.is_absolute() and str(scope_path).startswith(str(tmpdir) + os.sep):
                rows.append(("SCOPE_ANCHOR_FILE", scope))
    for name in (".step3-plan-review-result.env", ".step3-review-result.env"):
        env_path = tmpdir / name
        env_rows = list(rows)
        # Preserve each env's own ROUND_NUM (resolve_artifact_round's top-precedence
        # key) so the MAV post phase stays idempotent across re-runs. The legacy
        # persist-retally-step3-env.sh kept ROUND_NUM via its preserve-most rewrite;
        # this native port writes a fixed subset, so carry ROUND_NUM explicitly.
        prior_round = _read_kv_file(path=env_path).get("ROUND_NUM", "")
        if prior_round and re.fullmatch(r"[0-9]+", prior_round):
            env_rows.append(("ROUND_NUM", prior_round))
        phase_driver_write_result_env(path=env_path, kvs=env_rows)
    _emit_kv(key="PERSIST_RETALLY_STATUS", value="ok")
    return 0


def _step3_clear_downstream_sentinels(tmpdir: Path) -> None:
    """Remove the downstream Step 3 completion sentinels and per-round
    gate-b-postapply markers. Shared by direct-review, pause-hygiene, and
    auto-continuation re-entry (port of design-step3-state.sh's rm -f set).
    """
    for rel in (
        ".completed/step-3",
        ".completed/step-3.5",
        ".completed/step-3-terminal",
        ".step3-terminal-persisted-this-run",
        ".completed/step-3b",
        ".completed/step-4",
        ".completed/step-4b",
    ):
        (tmpdir / rel).unlink(missing_ok=True)
    for path in tmpdir.glob(".gate-b-postapply-ready-*"):
        path.unlink(missing_ok=True)


def _step3_cleanup_settled_loop_state(*, tmpdir: Path, max_round: int) -> None:
    """Drop settled per-round phase / pre-apply artifacts for rounds at or below
    max_round (port of design-step3-state.sh cleanup_settled_step3_loop_state).
    Symlinks are skipped, matching the legacy guard.
    """
    for pattern, prefix, suffix in (
        (".step3-round-*.phase", ".step3-round-", ".phase"),
        ("plan-pre-apply-round-*.txt", "plan-pre-apply-round-", ".txt"),
    ):
        for path in tmpdir.glob(pattern):
            if path.is_symlink():
                continue
            stem = path.name[len(prefix):-len(suffix)]
            if re.fullmatch(r"[0-9]+", stem) and int(stem, 10) <= max_round:
                path.unlink(missing_ok=True)


def step3_state(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review step3-state")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--direct-review-entry", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--direct-review-pause-hygiene", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--auto-continuation-entry", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--gate-b-bypass", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    (tmpdir / ".completed").mkdir(parents=True, exist_ok=True)
    count = _read_count(tmpdir)
    if ns.auto_continuation_entry:
        # Auto-continuation clears downstream state and settles prior rounds, but
        # is unconditional (no .step3-reentry gate) and does not restore step-2a/2b.
        _step3_clear_downstream_sentinels(tmpdir)
        _step3_cleanup_settled_loop_state(tmpdir=tmpdir, max_round=count)
        state = "auto-continuation-entry"
    elif ns.gate_b_bypass:
        # Port of legacy design-step3-state.sh gate-b-bypass: refuse when the
        # step-3.5 sentinel already exists, otherwise write both the step-3 and
        # step-3.5 completion sentinels (supplementing a pre-existing step-3).
        if (tmpdir / ".completed" / "step-3.5").exists():
            state = "refused-partial-gate-b-bypass"
        else:
            step3_loop_write_completed_step3(tmpdir)
            state = "gate-b-bypass"
    elif ns.direct_review_entry or ns.direct_review_pause_hygiene:
        # Direct-review / pause-hygiene re-entry only mutates state when the
        # .step3-reentry breadcrumb is present (set by the Step 3 entry fence on
        # backward re-entry); first-time entry is a no-op.
        action = "direct-review-entry" if ns.direct_review_entry else "direct-review-pause-hygiene"
        if not (tmpdir / ".step3-reentry").is_file():
            state = "noop"
        else:
            _step3_clear_downstream_sentinels(tmpdir)
            for name in ("step-1e", "step-2a", "step-2b", "step-2b.5"):
                (tmpdir / ".completed" / name).touch()
            if ns.direct_review_entry:
                # direct-review-entry (not pause-hygiene) also settles prior rounds,
                # drops the accumulated finding/OOS artifacts, and consumes the
                # re-entry breadcrumb.
                _step3_cleanup_settled_loop_state(tmpdir=tmpdir, max_round=count)
                for rel in (
                    "accepted-plan-findings-all.md",
                    ".accepted-plan-findings-all.prev.md",
                    ".step3-applied-finding-keys.tsv",
                    "oos-accepted-design.md",
                    ".oos-accepted-design.prev.md",
                    ".step3-reentry",
                ):
                    (tmpdir / rel).unlink(missing_ok=True)
            state = action
    else:
        state = "ok"
    _emit_kv(key="STEP3_STATE", value=state)
    _emit_kv(key="REVIEW_ROUND_COUNT", value=count)
    return 0


def _append_canonical_round_timing(*, tmpdir: Path, round_num: int, start_s: int, end_s: int) -> None:
    """Append a canonical ``v1 round`` timing row for a design plan-review round.

    The Review Phase Detail renderer (``progress_report._timing_round_windows``)
    only reads the canonical ``v1 | round | ...`` row written by
    ``TimingLedger.record_round``; the prior bespoke 6-column row failed the
    ``cols[0] == "v1"`` / ``cols[1] == "round"`` gate and was dropped, so both the
    Time and Cost columns rendered ``—`` (issue #5444). Idempotent on
    (skill=design, round_num) so the normal round-meta callsite and the MAV
    recorder never double-record the same round.
    """
    ledger = tmpdir / "timing-ledger.tsv"
    round_s = str(round_num)
    if ledger.is_file():
        try:
            existing = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            existing = []
        for line in existing:
            cols = line.split("\t")
            # Canonical layout from TimingLedger.record_round: cols[0]="v1",
            # cols[1]="round", cols[3]=skill, cols[5]=round_n (>= 8 columns).
            if len(cols) >= 8 and cols[0] == "v1" and cols[1] == "round" and cols[3] == "design" and cols[5] == round_s:  # noqa: PLR2004 - canonical round row has >= 8 columns
                return
    TimingLedger(path=ledger, skill="design").record_round(
        skill="design",
        step="design Step 3 — plan review",
        round_n=round_num,
        start_s=start_s,
        end_s=end_s,
        accepted=0,
        rejected=0,
    )


def _record_design_round_timing_from_start_file(*, tmpdir: Path, round_num: int) -> None:
    """Record canonical per-round timing for a completed design plan-review round.

    Reads ``round-start-s`` (written at round start by
    ``persist_design_round_start_s``) and records the canonical window through
    ``_append_canonical_round_timing`` so the Review Phase Detail Time/Cost
    columns render on the normal (non-MAV) loop path (issue #5444). Best effort:
    a missing or malformed start file is skipped silently so round-meta
    persistence is never blocked.
    """
    start_file = tmpdir / "plan-review" / f"round-{round_num}" / "round-start-s"
    try:
        start_s = int(start_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return
    if start_s <= 0:
        return
    _append_canonical_round_timing(tmpdir=tmpdir, round_num=round_num, start_s=start_s, end_s=int(time.time()))


def record_plan_review_round_timing(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review record-round-timing")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--round", type=int, required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--start-s", type=int, required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--end-s", type=int, required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    _append_canonical_round_timing(tmpdir=tmpdir, round_num=ns.round, start_s=ns.start_s, end_s=ns.end_s)
    round_dir = tmpdir / "plan-review" / f"round-{ns.round}"
    if round_dir.is_dir() and not round_dir.is_symlink():
        summary = round_dir / "round-summary.env"
        if not summary.exists():
            _write_atomic(path=summary, content=f"ROUND_NUM={ns.round}\n")
    _emit_kv(key="RECORD_ROUND_TIMING_STATUS", value="ok")
    return 0


def tally_plan_review(argv: Sequence[str]) -> int:
    return plan_review_tally.main(list(argv))


def _read_phase(*, tmpdir: Path, round_num: int) -> str:
    path = tmpdir / f".step3-round-{round_num}.phase"
    if path.is_file() and not path.is_symlink():
        return path.read_text(encoding="utf-8", errors="replace").strip()
    return ""


def _resolve_findings_file(*, tmpdir: Path, round_num: int) -> Path:
    default = tmpdir / "accepted-plan-findings.md"
    approval_env = tmpdir / f".gate-b-per-round-approval-round-{round_num}.env"
    if not approval_env.is_file() or approval_env.is_symlink():
        return default
    findings_file = default
    for line in approval_env.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("FINDINGS_FILE="):
            findings_file = Path(line.split("=", 1)[1])
    if findings_file != default:
        try:
            resolved = findings_file.resolve()
            tmp_resolved = tmpdir.resolve()
            if resolved.is_file() and not resolved.is_symlink() and str(resolved).startswith(f"{tmp_resolved}{os.sep}"):
                return resolved
        except OSError:
            pass
    return default


def _consume_approval_env(*, tmpdir: Path, round_num: int) -> None:
    with contextlib.suppress(FileNotFoundError):
        (tmpdir / f".gate-b-per-round-approval-round-{round_num}.env").unlink()


def _exec_pause_save(tmpdir: Path) -> int:
    issue = os.environ.get("ISSUE_NUMBER", "")
    cmd = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "design", "pause-save", "--design-tmpdir", str(tmpdir)]
    if issue:
        cmd.extend(["--issue", issue])
    override = os.environ.get("RUN_STEP3_DESIGN_PAUSE_SAVE_SH", "")
    if override:
        cmd = [override, "--design-tmpdir", str(tmpdir)]
        if issue:
            cmd.extend(["--issue", issue])
    return _run_command(argv=cmd, capture=False).returncode


def _run_post_apply(*, tmpdir: Path, round_num: int, values: dict[str, str]) -> int:
    override = os.environ.get("RUN_STEP3_POSTPLAN_EMIT_SH", "")
    if override:
        base = [override]
    else:
        base = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "design", "postplan-emit"]
    # #4847: run the postplan validator from the consumer-repo cwd so it derives
    # the consumer repo (repo_roots.consumer_repo_root) and resolves
    # plan-command script paths against it. Without this override _run_command
    # forces the plugin-cache cwd, the consumer-root derivation collapses, and
    # consumer-only scripts absent from a lagging plugin cache are false-flagged
    # missing-script (#4490 recurrence). cwd=None falls back to _REPO_ROOT when
    # cwd is not a git tree (no consumer repo to target), preserving prior behavior.
    proc = _run_command(argv=[*base, "--design-tmpdir", str(tmpdir), "--with-plan-size"], cwd=consumer_repo_root())
    rc = proc.returncode
    if rc == 0:
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
        return 0
    if rc == POSTPLAN_RC_PAUSE:
        return _exec_pause_save(tmpdir)
    if rc == POSTPLAN_RC_PLAN_SIZE_WARN:
        logging_util.emit_kv(key="WARN", value=f"plan-size trigger (postplan rc=12) in continuation (round {round_num}): proceeding as warning-only")
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
        return 0
    values["POSTPLAN_RC"] = str(rc)
    if rc in {10, 13}:
        return POSTPLAN_RC_OPERATOR
    return 33


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


def persist_design_round_start_s(*, design_tmpdir: str | Path, round_num: int, start_s: int) -> int:
    ok, _message, tmpdir = _validate_tmpdir_arg(design_tmpdir)
    if not ok:
        return 1
    round_dir = tmpdir / "plan-review" / f"round-{round_num}"
    if (tmpdir / "plan-review").is_symlink():
        return 0
    try:
        round_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    start_file = round_dir / "round-start-s"
    if start_file.exists() or start_file.is_symlink():
        return 0
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(start_file, flags, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"{start_s}\n")  # pyright: ignore[reportUnusedCallResult]
    except OSError:
        return 0
    return 0


def _read_bool_param(*, tmpdir: Path, key: str, default: bool = False) -> bool:
    return json_get_bool(path=tmpdir / "run-params.json", key=key, default=default)


def _run_round_subprocess(*, tmpdir: Path, argv: Sequence[str]) -> tuple[int, str]:
    env = os.environ.copy()
    _ = env.setdefault("CLAUDE_PLUGIN_ROOT", str(_plugin_root()))
    _ = env.setdefault("PLUGIN_ROOT", str(_plugin_root()))
    env["DESIGN_TMPDIR"] = str(tmpdir)
    proc = _run_command(argv=[str(Path(os.environ["RUN_STEP3_PLAN_REVIEW_LOOP_SH"])), *argv], env=env)
    return proc.returncode, proc.stdout + proc.stderr


def run_plan_review_round(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review round")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--round-num", type=int, default=1)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--prune-round-num", type=int, default=0)  # pyright: ignore[reportUnusedCallResult]
    ns, _extra = parser.parse_known_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    round_num = ns.round_num
    plan_file = tmpdir / "plan.txt"
    feature_file = tmpdir / "feature-description.txt"
    rc, _ = plan_review_round.execute_round(
        design=tmpdir,
        round_num=round_num,
        prune_round_num=ns.prune_round_num or round_num,
        codex_present=os.environ.get("CODEX_BINARY_FOUND", "false") or "false",
        cursor_present=os.environ.get("CURSOR_BINARY_FOUND", "false") or "false",
        plan_file=plan_file,
        feature_file=feature_file,
    )
    return rc


def _snapshot_plan(*, tmpdir: Path, round_num: int) -> Path:
    snapshot = tmpdir / f"plan-pre-apply-round-{round_num}.txt"
    if not snapshot.exists():
        _ = shutil.copyfile(tmpdir / "plan.txt", snapshot)
    return snapshot


def _run_dedup(*, tmpdir: Path, round_num: int, values: dict[str, str]) -> int:
    snapshot = _snapshot_plan(tmpdir=tmpdir, round_num=round_num)
    override = os.environ.get("RUN_STEP3_DEDUP_PLAN_SH", "")
    if override:
        base = [override]
    else:
        base = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan-review", "gate-b-dedup"]
    proc = _run_command(argv=[*base, "--design-tmpdir", str(tmpdir), "--snapshot-trailers"])
    rc = proc.returncode
    if rc == 0:
        proc = _run_command(argv=[*base, "--design-tmpdir", str(tmpdir), "--dedup"])
        rc = proc.returncode
    if rc != 0:
        values["DEDUP_RC"] = str(rc)
        if snapshot.is_file():
            _ = shutil.copyfile(snapshot, tmpdir / "plan.txt")
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
        return 22
    clear = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "design", "dialectic-clear-stale", "--design-tmpdir", str(tmpdir), "--reason", "plan-rewrite"])
    if clear.returncode != 0:
        print("**⚠ plan-review: dialectic-clear-stale failed after dedup; stale clarifier artifacts may linger (Gate C fingerprint binding still gates debate).**", file=sys.stderr)
    _ = (tmpdir / f".gate-b-postapply-ready-{round_num}").touch()
    with contextlib.suppress(FileNotFoundError):
        (tmpdir / f".gate-b-per-round-approval-round-{round_num}.env").unlink()
    return 0


def _write_design_round_meta(*, tmpdir: Path, round_num: int) -> None:
    """Persist ``round-meta.json`` for a completed plan-review round.

    Every round that ran a full panel+vote must write ``round-meta.json`` so the
    Review Phase Detail table (``progress_report._completed_round_dirs``) counts
    it. The terminal 0-accepted stop round never enters the apply/revise path, so
    without an explicit write here it is dropped from the table while the
    run-summary header still counts it (header vs table round-count mismatch).

    Also records the round's canonical timing window (issue #5444) so the same
    table's Time and Cost columns render on the normal loop path.
    """
    round_dir = str(tmpdir / "plan-review" / f"round-{round_num}")
    round_meta_override = os.environ.get("WRITE_DESIGN_ROUND_META_SH")
    if round_meta_override:
        # Test/harness override only; production uses the migrated Python CLI verb below.
        if Path(round_meta_override).exists() and os.access(round_meta_override, os.X_OK):
            _ = _run_command(argv=[round_meta_override, "--round-dir", round_dir])
    else:
        _ = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "progress", "write-design-round-meta", "--round-dir", round_dir])
    # Record the canonical per-round timing window so the Review Phase Detail
    # Time/Cost columns render on the normal loop path, not only the MAV path
    # (issue #5444). Best effort; never blocks round-meta persistence.
    _record_design_round_timing_from_start_file(tmpdir=tmpdir, round_num=round_num)


def _run_apply(*, tmpdir: Path, round_num: int, values: dict[str, str]) -> int:
    accepted = _count_accepted(tmpdir)
    values["ACCEPTED_COUNT"] = str(accepted)
    if accepted == 0:
        _consume_approval_env(tmpdir=tmpdir, round_num=round_num)
        _write_design_round_meta(tmpdir=tmpdir, round_num=round_num)
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
        return 0
    findings_file = _resolve_findings_file(tmpdir=tmpdir, round_num=round_num)
    if findings_file != tmpdir / "accepted-plan-findings.md" and findings_file.is_file() and findings_file.stat().st_size > 0:
        _ = shutil.copyfile(findings_file, tmpdir / "accepted-plan-findings.md")
    if not findings_file.is_file() or findings_file.is_symlink() or findings_file.stat().st_size == 0:
        _write_atomic(path=tmpdir / "accepted-plan-findings.md", content="")
        _consume_approval_env(tmpdir=tmpdir, round_num=round_num)
        _write_design_round_meta(tmpdir=tmpdir, round_num=round_num)
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
        return 0
    snapshot = _snapshot_plan(tmpdir=tmpdir, round_num=round_num)
    current_phase = _read_phase(tmpdir=tmpdir, round_num=round_num)
    postapply_ready = (tmpdir / f".gate-b-postapply-ready-{round_num}").is_file()
    if snapshot.is_file() and (tmpdir / "plan.txt").is_file():
        try:
            plan_changed = snapshot.read_bytes() != (tmpdir / "plan.txt").read_bytes()
        except OSError:
            plan_changed = False
        if plan_changed:
            if current_phase == "awaiting-post-apply" or postapply_ready:
                return _run_dedup(tmpdir=tmpdir, round_num=round_num, values=values)
            if current_phase == "awaiting-revise":
                _ = shutil.copyfile(snapshot, tmpdir / "plan.txt")
    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-revise")
    with contextlib.suppress(FileNotFoundError):
        for pattern in ("scout-plan-manifest.json",):
            path = tmpdir / pattern
            if path.exists():
                path.unlink()
        for path in tmpdir.glob("scout-plan-manifest.json.candidate.*"):
            path.unlink(missing_ok=True)
        for path in tmpdir.glob("scout-plan-manifest.json.filtered.*"):
            path.unlink(missing_ok=True)
    override = os.environ.get("RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH", "")
    if override:
        cmd = [override]
    else:
        cmd = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan", "revise-waterfall"]
    proc = _run_command(
        argv=[
            *cmd,
            "--design-tmpdir",
            str(tmpdir),
            "--plan-file",
            str(tmpdir / "plan.txt"),
            "--findings-file",
            str(tmpdir / "accepted-plan-findings.md"),
            "--feature-file",
            str(tmpdir / "feature-description.txt"),
            "--round-num",
            str(round_num),
            "--codex-binary-found",
            os.environ.get("CODEX_BINARY_FOUND", ""),
            "--cursor-binary-found",
            os.environ.get("CURSOR_BINARY_FOUND", ""),
            "--patch-format",
            "file-replacement",
        ]
    )
    revise_status = _parse_kv_text(proc.stdout).get("REVISE_STATUS", "")
    if proc.returncode != 0 or revise_status not in {"ok", "ok-fallback"}:
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
        return 21
    _write_design_round_meta(tmpdir=tmpdir, round_num=round_num)
    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-post-apply")
    return _run_dedup(tmpdir=tmpdir, round_num=round_num, values=values)


def _finding_dedup_key(block: str) -> str:
    """Stable cross-round identity for an accepted FINDING block, keyed on
    Location + Concern (falls back to the block body without its numbered header
    when both are absent). Normalized so trivial whitespace differences between
    rounds do not defeat the dedup.
    """

    def _field(label: str) -> str:
        match = re.search(rf"(?mi)^- \*\*{label}\*\*:\s*(.*?)\s*$", block)
        return match.group(1) if match else ""

    location = _field("Location")
    concern = _field("Concern")
    if location or concern:
        raw = f"{location}\x1f{concern}"
    else:
        raw = re.sub(r"(?m)^### FINDING_[0-9]+:.*$", "", block)
    return re.sub(r"\s+", " ", raw).strip().lower()


def _read_applied_finding_keys(tmpdir: Path, *, before_round: int) -> set[str]:
    """Finding keys recorded in rounds strictly before ``before_round``."""
    path = tmpdir / ".step3-applied-finding-keys.tsv"
    if not path.is_file() or path.is_symlink():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "\t" not in line:
            continue
        round_field, key = line.split("\t", 1)
        if key and re.fullmatch(r"[0-9]+", round_field) and int(round_field, 10) < before_round:
            keys.add(key)
    return keys


def _read_all_applied_finding_keys(tmpdir: Path) -> set[str]:
    """Every finding key in the applied-finding ledger, across all rounds.

    Unlike :func:`_read_applied_finding_keys` (which filters to rounds before a
    cutoff for the continuation decision), this returns the cumulative set so the
    Step 4 rejected-findings report can drop a finding that was applied in any
    earlier round but re-raised and rejected in a later round (issue #4849).
    """
    path = tmpdir / ".step3-applied-finding-keys.tsv"
    if not path.is_file() or path.is_symlink():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "\t" not in line:
            continue
        round_field, key = line.split("\t", 1)
        if key and re.fullmatch(r"[0-9]+", round_field):
            keys.add(key)
    return keys


def _record_applied_finding_keys(*, tmpdir: Path, round_num: int, keys: Sequence[str]) -> None:
    """Record this round's accepted finding keys in the applied-finding ledger,
    idempotently (rows for ``round_num`` are rewritten, not duplicated).
    """
    path = tmpdir / ".step3-applied-finding-keys.tsv"
    rows: list[str] = []
    if path.is_file() and not path.is_symlink():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "\t" not in line:
                continue
            round_field = line.split("\t", 1)[0]
            if re.fullmatch(r"[0-9]+", round_field) and int(round_field, 10) != round_num:
                rows.append(line)
    seen: set[str] = set()
    for key in keys:
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(f"{round_num}\t{key}")
    _write_atomic(path=path, content="".join(f"{row}\n" for row in rows))


# A finding tagged ``[ALREADY_ADDRESSED]`` by a reviewer is one the current plan
# already satisfies (issue #4920). Such findings are suppressed from the Step 4
# not-adopted report, and their concern key is laddered across rounds so the same
# already-satisfied concern does not recur once any round flags it.
_ALREADY_ADDRESSED_RE = re.compile(r"\[ALREADY_ADDRESSED\]", re.IGNORECASE)
_ALREADY_ADDRESSED_LEDGER = ".step3-already-addressed-finding-keys.tsv"


def _read_already_addressed_finding_keys(tmpdir: Path) -> set[str]:
    """Cumulative concern keys flagged ``[ALREADY_ADDRESSED]`` in any round."""
    path = tmpdir / _ALREADY_ADDRESSED_LEDGER
    if not path.is_file() or path.is_symlink():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key = line.strip()
        if key:
            keys.add(key)
    return keys


def _record_already_addressed_finding_keys(*, tmpdir: Path, keys: Sequence[str]) -> None:
    """Merge ``keys`` into the already-addressed ledger, idempotently and sorted."""
    existing = _read_already_addressed_finding_keys(tmpdir)
    merged = existing | {key for key in keys if key}
    if merged == existing:
        return
    _write_atomic(
        path=tmpdir / _ALREADY_ADDRESSED_LEDGER,
        content="".join(f"{key}\n" for key in sorted(merged)),
    )


def _already_addressed_keys_in_rejected(tmpdir: Path) -> list[str]:
    """Concern keys of rejected blocks tagged ``[ALREADY_ADDRESSED]`` this round."""
    path = tmpdir / "rejected-findings.md"
    if not path.is_file() or path.is_symlink():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker_re in (r"(?m)^### \[Plan Review\] ", r"(?m)^### FINDING_[0-9]+:"):
        matches = list(re.finditer(marker_re, text))
        if not matches:
            continue
        keys: list[str] = []
        for idx, match in enumerate(matches):
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            block = text[match.start():end]
            if _ALREADY_ADDRESSED_RE.search(block):
                # Key on the tag-stripped block so a later round that re-raises
                # the same concern WITHOUT the tag matches this laddered key.
                key = _finding_dedup_key(_ALREADY_ADDRESSED_RE.sub("", block))
                if key:
                    keys.append(key)
        return keys
    return []


def _filter_rejected_findings_body(*, text: str, applied: set[str], marker_re: str) -> tuple[str, bool]:
    """Filter ``text`` blocks starting with ``marker_re``, dropping suppressed keys.

    A block is dropped when its finding key is in ``applied`` (applied in a prior
    round, or flagged already-addressed) or when the block itself carries the
    ``[ALREADY_ADDRESSED]`` tag. Returns ``(filtered_body, had_blocks)`` where
    ``had_blocks`` is true when at least one block header matched ``marker_re``.
    """
    matches = list(re.finditer(marker_re, text))
    if not matches:
        return "", False
    kept: list[str] = []
    prefix = text[: matches[0].start()]
    if prefix:
        kept.append(prefix)
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[match.start():end]
        key = _finding_dedup_key(block)
        if (key and key in applied) or _ALREADY_ADDRESSED_RE.search(block):
            continue
        kept.append(block)
    return "".join(kept), True


REJECTED_FINDINGS_REPORT_HEADING = "## Considered Plan Review Suggestions (Not Adopted)"
REJECTED_FINDINGS_REPORT_ANNOTATION = (
    "These reviewer suggestions were considered but not adopted. Some may already "
    "be addressed by the current plan; they are not automatically unimplemented gaps."
)


def _format_rejected_findings_report(body: str, *, report_framing: bool) -> str:
    if not report_framing or not body:
        return body
    return (
        f"{REJECTED_FINDINGS_REPORT_HEADING}\n\n"
        f"{REJECTED_FINDINGS_REPORT_ANNOTATION}\n\n"
        f"{body}"
    )


def emit_rejected_findings(argv: Sequence[str]) -> int:
    """Emit the Step 4 rejected-findings body with already-applied findings removed.

    The per-round tally overwrites ``rejected-findings.md`` with only the final
    round's not-accepted findings. When a later round re-raises a finding that an
    earlier round already accepted and applied, that finding lands here and would
    otherwise be reported to the operator under "Unimplemented Plan Review
    Suggestions" — even though it was implemented (issue #4849). Reuse the
    cross-round dedup keying (#4808) to drop any block whose finding key is in the
    cumulative applied-finding ledger.

    The on-disk ``rejected-findings.md`` is left untouched (still committed to the
    run log for audit); only this Step 4 emit surface is filtered. Output is the
    filtered body written verbatim to stdout, byte-faithful to the tally's block
    concatenation.
    """
    parser = argparse.ArgumentParser(prog="cli.py plan-review emit-rejected")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--report-framing", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    path = tmpdir / "rejected-findings.md"
    if path.is_symlink() or not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return 0
    applied = _read_all_applied_finding_keys(tmpdir) | _read_already_addressed_finding_keys(tmpdir)
    if not applied and not _ALREADY_ADDRESSED_RE.search(text):
        print(_format_rejected_findings_report(body=text, report_framing=ns.report_framing), end="")
        return 0
    filtered, had_blocks = _filter_rejected_findings_body(
        text=text, applied=applied, marker_re=r"(?m)^### \[Plan Review\] "
    )
    if had_blocks:
        print(_format_rejected_findings_report(body=filtered, report_framing=ns.report_framing), end="")
        return 0
    filtered, had_blocks = _filter_rejected_findings_body(
        text=text, applied=applied, marker_re=r"(?m)^### FINDING_[0-9]+:"
    )
    if had_blocks:
        print(_format_rejected_findings_report(body=filtered, report_framing=ns.report_framing), end="")
        return 0
    print(
        "WARN=emit-rejected: applied-finding ledger present but rejected-findings.md "
        "has no recognizable blocks; emitting empty body",
        file=sys.stderr,
    )
    print(end="")
    return 0


def plan_review_continuation(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review continuation")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--approve-requested", choices=("true", "false"), required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    review_count = _read_count(tmpdir)
    result_env = _read_kv_file(path=tmpdir / ".step3-review-result.env")
    degraded = 1 if result_env.get("DEGRADED_PANEL") in {"1", "true"} else 0
    tally_status = result_env.get("TALLY_PLAN_REVIEW_STATUS", "")
    loop_status = result_env.get("LOOP_STATUS", "")
    step3_reason = result_env.get("REASON", "")
    panel_pruned_empty = result_env.get("PANEL_PRUNED_EMPTY", "")
    findings = _parse_accepted_findings(tmpdir)
    blocks = [finding.block for finding in findings]
    severities = [finding.severity_raw for finding in findings]
    structured = bool(blocks) and all(sev in _STRUCTURED_GATE_B_SEVERITIES for sev in severities)
    accepted = len(blocks)
    nit = sum(1 for sev in severities if sev == "nit")
    non_nit = max(0, accepted - nit)
    if structured:
        high = sum(1 for sev in severities if sev in {"blocking", "important"})
    else:
        high = sum(1 for block in blocks if re.search(r"critical|\bhigh\b|data loss|regression|missing required", block, re.IGNORECASE))
    # Cross-round convergence (#4808): a finding accepted and applied in a prior
    # round, when re-raised and re-accepted, must not keep the loop going. Key
    # each accepted block on Location + Concern, compare against the
    # applied-finding ledger from earlier rounds, and drive continuation off the
    # genuinely new findings only. The totals above stay reported as-is.
    prior_keys = _read_applied_finding_keys(tmpdir=tmpdir, before_round=review_count)
    block_keys = [_finding_dedup_key(block) for block in blocks]
    new_flags = [key not in prior_keys for key in block_keys]
    duplicate_accepted = sum(1 for is_new in new_flags if not is_new)
    new_count = sum(1 for is_new in new_flags if is_new)
    nit_new = sum(1 for sev, is_new in zip(severities, new_flags, strict=True) if is_new and sev == "nit")
    non_nit_new = max(0, new_count - nit_new)
    if structured:
        high_new = sum(1 for sev, is_new in zip(severities, new_flags, strict=True) if is_new and sev in {"blocking", "important"})
    else:
        high_new = sum(1 for block, is_new in zip(blocks, new_flags, strict=True) if is_new and re.search(r"critical|\bhigh\b|data loss|regression|missing required", block, re.IGNORECASE))
    plan_text = (tmpdir / "plan.txt").read_text(encoding="utf-8", errors="replace") if (tmpdir / "plan.txt").is_file() else ""
    diff_lines = 0
    for match in re.finditer(r"(?mi)^diff_lines:\s*([0-9]+)\s*$", plan_text):
        diff_lines = int(match.group(1), 10)
    structural_large = diff_lines > STRUCTURAL_DIFF_LINE_THRESHOLD or len(plan_text.splitlines()) > STRUCTURAL_PLAN_LINE_THRESHOLD
    cont = False
    reason = "small-clean"
    if tally_status == "ok" and loop_status == "complete":
        degraded = 0
    if step3_reason.startswith("ballot-items-lost") and accepted == 0 and degraded and tally_status == "ok" and loop_status == "zero-findings-degraded-panel":
        cont = True
        reason = "ballot-items-lost"
    elif ns.approve_requested == "true":
        reason = "explicit-approve"
    elif review_count >= ROUND_CAP:
        reason = "cap-reached"
    elif panel_pruned_empty == "true":
        # #5255: prune-to-empty means zero reviewers ran and zero findings were
        # produced, so the review has run dry. Converge instead of forcing the
        # round-5 re-probe; the degraded_exit terminal path in run_step3_review
        # preserves round provenance (#5194) so the plan still publishes.
        cont = False
        reason = "converged-pruned-empty"
    elif degraded and (high_new > 0 or non_nit_new > NON_NIT_CONTINUE_THRESHOLD):
        cont = True
        reason = "degraded-panel"
    elif high_new > 0:
        cont = True
        reason = "high-accepted"
    elif non_nit_new > NON_NIT_CONTINUE_THRESHOLD:
        cont = True
        reason = "non-nit-accepted"
    elif structural_large and non_nit > 0 and review_count < STRUCTURAL_MIN_REVIEW_ROUNDS:
        cont = True
        reason = "structural-or-large-change"
    no_new_material_findings = high_new == 0 and non_nit_new <= NON_NIT_CONTINUE_THRESHOLD
    has_material_findings = high > 0 or non_nit > NON_NIT_CONTINUE_THRESHOLD
    if not cont and reason == "small-clean" and duplicate_accepted > 0 and no_new_material_findings and has_material_findings:
        reason = "converged-no-new-findings"
    _record_applied_finding_keys(tmpdir=tmpdir, round_num=review_count, keys=block_keys)
    _record_already_addressed_finding_keys(tmpdir=tmpdir, keys=_already_addressed_keys_in_rejected(tmpdir))
    for key, value in (
        ("PLAN_REVIEW_CONTINUE", "true" if cont else "false"),
        ("PLAN_REVIEW_CONTINUE_REASON", reason),
        ("REVIEW_ROUND_COUNT", str(review_count)),
        ("REVIEW_ROUND_CAP", str(ROUND_CAP)),
        ("ACCEPTED_COUNT", str(accepted)),
        ("NIT_ACCEPTED_COUNT", str(nit)),
        ("NON_NIT_ACCEPTED_COUNT", str(non_nit)),
        ("HIGH_ACCEPTED_COUNT", str(high)),
        ("NEW_HIGH_ACCEPTED_COUNT", str(high_new)),
        ("NEW_NON_NIT_ACCEPTED_COUNT", str(non_nit_new)),
        ("DUPLICATE_ACCEPTED_COUNT", str(duplicate_accepted)),
        ("DEGRADED_PANEL", str(degraded)),
        ("STRUCTURAL_OR_LARGE_CHANGE", "true" if structural_large else "false"),
    ):
        _emit_kv(key=key, value=value)
    return 0


def _run_continuation(tmpdir: Path, *, approve_requested: bool) -> dict[str, str]:
    override = os.environ.get("RUN_STEP3_CONTINUATION_SH", "")
    if override:
        cmd = [override]
    else:
        cmd = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan-review", "continuation"]
    env = os.environ.copy()
    env["DESIGN_TMPDIR"] = str(tmpdir)
    _ = env.setdefault("CLAUDE_PLUGIN_ROOT", str(_plugin_root()))
    proc = _run_command(argv=[*cmd, "--design-tmpdir", str(tmpdir), "--approve-requested", "true" if approve_requested else "false"], env=env)
    if proc.returncode != 0:
        return {"PLAN_REVIEW_CONTINUE": "false", "PLAN_REVIEW_CONTINUE_REASON": "continuation-failed"}
    out = _parse_kv_text(proc.stdout)
    if "PLAN_REVIEW_CONTINUE" not in out:
        return {"PLAN_REVIEW_CONTINUE": "false", "PLAN_REVIEW_CONTINUE_REASON": "continuation-malformed"}
    return out


def _round_args(*, tmpdir: Path, round_num: int) -> list[str]:
    return ["--design-tmpdir", str(tmpdir), "--round-num", str(round_num), "--prune-round-num", str(round_num)]


_ROUND_DIR_PRESERVE = frozenset({"round-start-s"})


def _is_pre_collection_terminal(values: dict[str, str]) -> bool:
    loop_status = values.get("LOOP_STATUS", "")
    agg = values.get("AGGREGATOR_STATUS", "")
    if loop_status == "zero-findings-degraded-panel":
        return True
    return loop_status == "panel-failed" and agg in {"skipped", "skipped-pruned-empty"}


def _clean_round_dir(*, tmpdir: Path, round_num: int) -> None:
    round_dir = tmpdir / "plan-review" / f"round-{round_num}"
    if not round_dir.is_dir() or round_dir.is_symlink():
        return
    status_link = round_dir / "reviewer-status.tsv"
    if status_link.is_symlink():
        with contextlib.suppress(OSError):
            status_link.unlink()
    for child in round_dir.iterdir():
        if child.name in _ROUND_DIR_PRESERVE:
            continue
        if child.is_file() and not child.is_symlink():
            with contextlib.suppress(OSError):
                child.unlink()


def _run_round_body(*, tmpdir: Path, round_num: int) -> tuple[int, dict[str, str]]:
    start_s = int(time.time())
    _ = persist_design_round_start_s(design_tmpdir=tmpdir, round_num=round_num, start_s=start_s)
    _clean_round_dir(tmpdir=tmpdir, round_num=round_num)
    if os.environ.get("RUN_STEP3_PLAN_REVIEW_LOOP_SH"):
        body_rc, out_text = _run_round_subprocess(tmpdir=tmpdir, argv=_round_args(tmpdir=tmpdir, round_num=round_num))
        values_pre = _parse_kv_text(out_text)
        round_status = tmpdir / "plan-review" / f"round-{round_num}" / "reviewer-status.tsv"
        # The subprocess round body normally produces reviewer-status.tsv (#4848); if an
        # injected loop override did not, materialize it here from the on-disk manifest +
        # collector-results.env so the SKILL.md table still works.
        if not round_status.is_file() or round_status.is_symlink():
            if round_status.is_symlink():
                with contextlib.suppress(OSError):
                    round_status.unlink()
            collect_override: str | None = None
            if _is_pre_collection_terminal(values_pre):
                collect_override = ""
                _ = (tmpdir / "collector-results.env").write_text("", encoding="utf-8")
            _ = plan_review_round.try_write_reviewer_status_tsv(
                design=tmpdir,
                round_num=round_num,
                collect_text=collect_override,
                header_fallback=True,
            )
        else:
            plan_review_round.sync_latest_reviewer_status(design=tmpdir, round_status=round_status)
            _ = plan_review_round.materialize_stable_reviewer_status_table(design=tmpdir, round_num=round_num)
    else:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            body_rc = run_plan_review_round(_round_args(tmpdir=tmpdir, round_num=round_num))
        out_text = buf.getvalue()
    print(out_text, end="")
    values = _parse_kv_text(out_text)
    result_env = _read_kv_file(path=tmpdir / ".step3-review-result.env")
    if not values.get("REASON") and result_env.get("REASON"):
        values["REASON"] = result_env["REASON"]
    loop_status = values.get("LOOP_STATUS", "panel-failed" if body_rc else "complete")
    if body_rc != 0 and loop_status not in {"tally-error", "degraded-empty-collector", "panel-failed"}:
        tally_status = values.get("TALLY_PLAN_REVIEW_STATUS", "")
        loop_status = "tally-error" if tally_status == "tally-error" else "panel-failed"
    if values.get("STEP3_REVIEW_LOOP_STATUS"):
        loop_status = values.get("LOOP_STATUS", loop_status)
    values["LOOP_STATUS"] = loop_status
    _ = plan_review_round.materialize_stable_reviewer_status_table(design=tmpdir, round_num=round_num)
    return body_rc, values


def _step3_emit_cap_reached(*, review_count: int) -> None:
    _emit_kv(key="NEXT_ACTION", value="step3b-bypass")
    _emit_kv(key="LOOP_STATUS", value="cap-reached")
    _emit_kv(key="TALLY_PLAN_REVIEW_STATUS", value="skipped-cap-reached")
    _emit_kv(key="INFO", value=f"cap reached; skipping review round {review_count + 1}")


def _apply_new_process_group(parser: argparse.ArgumentParser) -> None:
    if not hasattr(os, "setsid"):
        parser.exit(2, "cli.py plan-review run: --new-process-group failed: os.setsid is unavailable\n")
    try:
        os.setsid()
    except OSError as exc:
        parser.exit(2, f"cli.py plan-review run: --new-process-group failed: {exc}\n")


def run_step3_review(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review run")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--mode", default="loop")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--starting-round", type=_positive_int)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--read-result-env", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--no-preview", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--new-process-group", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns, _extra = parser.parse_known_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    if ns.read_result_env:
        result = tmpdir / ".step3-review-result.env"
        for key, value in phase_driver_read_result_env(path=result, allow_keys=[
            "NEXT_ACTION",
            "STEP3_REVIEW_LOOP_STATUS",
            "LOOP_STATUS",
            "TALLY_PLAN_REVIEW_STATUS",
            "ROUNDS_COMPLETED",
            "FINAL_ROUND_NUM",
            "ACCEPTED_COUNT",
            "DEGRADED_PANEL",
            "DEGRADED_PANEL_WARNING",
            "INVALID_SLOT_PANEL_WARNING",
            "REASON",
        ]):
            _emit_kv(key=key, value=value)
        return 0
    if ns.new_process_group:
        _apply_new_process_group(parser)
    approve_requested = _read_bool_param(tmpdir=tmpdir, key="approve_requested", default=False)
    round_num = ns.starting_round or (_read_count(tmpdir) + 1)
    degraded_exit = False
    degraded_values: dict[str, str] = {}

    while True:
        phase = _read_phase(tmpdir=tmpdir, round_num=round_num)
        if not phase:
            review_count = _read_count(tmpdir)
            if review_count >= ROUND_CAP:
                values = {"TALLY_PLAN_REVIEW_STATUS": "skipped-cap-reached", "LOOP_STATUS": "cap-reached"}
                phase_driver_write_result_env(
                    path=tmpdir / ".step3-review-cap.env",
                    kvs=[("LOOP_STATUS", "cap-reached"), ("TALLY_PLAN_REVIEW_STATUS", "skipped-cap-reached")],
                )
                for stale in ("accepted-plan-findings.md", "voting-tally.md"):
                    with contextlib.suppress(OSError):
                        (tmpdir / stale).unlink()
                step3_loop_write_completed_step3(tmpdir)
                _step3_emit_cap_reached(review_count=review_count)
                step3_loop_persist_envelope(design_tmpdir=tmpdir, status="cap-hit", round_num=review_count + 1, rounds_completed=review_count, final_round=review_count + 1, values=values)
                return 0
            _write_count(tmpdir=tmpdir, count=round_num)
            _body_rc, values = _run_round_body(tmpdir=tmpdir, round_num=round_num)
            rounds_done = _read_count(tmpdir)
            loop_status = values["LOOP_STATUS"]
            if loop_status == "cap-reached":
                step3_loop_write_completed_step3(tmpdir)
                step3_loop_emit_envelope(tmpdir=tmpdir, status="cap-hit", round_num=round_num, rounds_completed=max(0, round_num - 1), final_round=round_num, values=values)
                return 0
            if loop_status in {"tally-error", "degraded-empty-collector", "panel-failed"}:
                if loop_status in {"tally-error", "degraded-empty-collector"}:
                    _write_count(tmpdir=tmpdir, count=max(0, round_num - 1))
                else:
                    _write_count(tmpdir=tmpdir, count=max(round_num, rounds_done))
                step3_wrapper_write_completed_step3_only(tmpdir)
                step3_loop_emit_envelope(tmpdir=tmpdir, status=loop_status, round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            if loop_status == "main-agent-vote-required":
                _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
                step3_loop_emit_envelope(tmpdir=tmpdir, status="main-agent-vote-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            if loop_status in {"complete", "zero-findings-degraded-panel"}:
                values = _merge_step3_round_carry_warnings(values=values, carry=degraded_values)
                accepted = _count_accepted(tmpdir) or int(values.get("ACCEPTED_COUNT", "0") or "0")
                values["ACCEPTED_COUNT"] = str(accepted)
                for key in _STEP3_ROUND_CARRY_KEYS:
                    if values.get(key):
                        degraded_values[key] = values[key]
                if loop_status == "zero-findings-degraded-panel":
                    phase_driver_write_result_env(
                        path=tmpdir / ".step3-review-result.env",
                        kvs=[
                            ("NEXT_ACTION", "step3b"),
                            ("LOOP_STATUS", "zero-findings-degraded-panel"),
                            # #5194: persist round provenance so design_publish.review_provenance()
                            # does not read rounds=0 and refuse to publish a cleanly-reviewed plan.
                            ("ROUNDS_COMPLETED", str(round_num)),
                            ("REVIEW_ROUND_COUNT", str(round_num)),
                            ("PANEL_PRUNED_EMPTY", values.get("PANEL_PRUNED_EMPTY", "true")),
                            ("TALLY_PLAN_REVIEW_STATUS", values.get("TALLY_PLAN_REVIEW_STATUS", "ok")),
                            ("ACCEPTED_COUNT", str(accepted)),
                            ("DEGRADED_PANEL", values.get("DEGRADED_PANEL", "0")),
                            ("DEGRADED_PANEL_WARNING", values.get("DEGRADED_PANEL_WARNING", "")),
                            ("INVALID_SLOT_PANEL_WARNING", values.get("INVALID_SLOT_PANEL_WARNING", "")),
                            ("REASON", values.get("REASON", "")),
                        ],
                    )
                    degraded_exit = True
                    degraded_values = dict(values)
                if accepted == 0:
                    _write_design_round_meta(tmpdir=tmpdir, round_num=round_num)
                    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
                elif approve_requested:
                    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
                    step3_loop_emit_envelope(tmpdir=tmpdir, status="per-round-approval-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                    return 0
                else:
                    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
                continue
            _emit_kv(key="WARN", value=f"missing or invalid LOOP_STATUS={loop_status!r}; treating as panel-failed")
            step3_wrapper_write_completed_step3_only(tmpdir)
            step3_loop_emit_envelope(tmpdir=tmpdir, status="panel-failed", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
            return 0

        if phase == "awaiting-revise":
            values: dict[str, str] = dict(degraded_values)
            apply_rc = _run_apply(tmpdir=tmpdir, round_num=round_num, values=values)
            if apply_rc != 0:
                step3_loop_emit_envelope(tmpdir=tmpdir, status="main-agent-apply-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            continue

        if phase == "awaiting-apply":
            approval_env = tmpdir / f".gate-b-per-round-approval-round-{round_num}.env"
            if approve_requested and not approval_env.is_file():
                step3_loop_emit_envelope(tmpdir=tmpdir, status="per-round-approval-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=degraded_values)
                return 0
            values = dict(degraded_values)
            apply_rc = _run_apply(tmpdir=tmpdir, round_num=round_num, values=values)
            if apply_rc != 0:
                step3_loop_emit_envelope(tmpdir=tmpdir, status="main-agent-apply-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            continue

        if phase in {"awaiting-post-apply", "awaiting-postplan-operator"}:
            if phase == "awaiting-postplan-operator":
                sentinel = tmpdir / f".postplan-operator-continue-{round_num}"
                if sentinel.is_file():
                    with contextlib.suppress(FileNotFoundError):
                        sentinel.unlink()
                    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
                    continue
                step3_loop_emit_envelope(tmpdir=tmpdir, status="postplan-operator-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=_step3_round_carry_values(degraded_exit=degraded_exit, degraded_values=degraded_values))
                return 0
            postapply_ready = tmpdir / f".gate-b-postapply-ready-{round_num}"
            if not postapply_ready.is_file():
                values = _step3_round_carry_values(degraded_exit=degraded_exit, degraded_values=degraded_values)
                dedup_rc = _run_dedup(tmpdir=tmpdir, round_num=round_num, values=values)
                if dedup_rc != 0:
                    step3_loop_emit_envelope(tmpdir=tmpdir, status="main-agent-apply-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                    return 0
            values = _step3_round_carry_values(degraded_exit=degraded_exit, degraded_values=degraded_values)
            post_rc = _run_post_apply(tmpdir=tmpdir, round_num=round_num, values=values)
            if post_rc == 0:
                continue
            if post_rc == POSTPLAN_RC_OPERATOR:
                _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-postplan-operator")
                step3_loop_emit_envelope(tmpdir=tmpdir, status="postplan-operator-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            step3_loop_emit_envelope(tmpdir=tmpdir, status="postplan-failed", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
            return 0

        if phase == "awaiting-continuation":
            _write_count(tmpdir=tmpdir, count=round_num)
            cont = _run_continuation(tmpdir=tmpdir, approve_requested=approve_requested)
            if cont.get("PLAN_REVIEW_CONTINUE") == "true":
                with contextlib.suppress(FileNotFoundError):
                    (tmpdir / ".step3-review-result.env").unlink()
                _ = _run_command(
                    argv=[
                        sys.executable,
                        str(_plugin_root() / "python" / "cli.py"),
                        "plan-review",
                        "step3-state",
                        "--design-tmpdir",
                        str(tmpdir),
                        "--auto-continuation-entry",
                    ]
                )
                with contextlib.suppress(FileNotFoundError):
                    (tmpdir / ".step3-entry-plan-printed").unlink()
                round_num += 1
                degraded_exit = False
                degraded_values = _step3_round_carry_values(degraded_exit=False, degraded_values=degraded_values)
                continue
            if degraded_exit:
                step3_loop_write_completed_step3(tmpdir)
                step3_loop_write_terminal_step3(tmpdir)
                _emit_kv(key="NEXT_ACTION", value="step3b")
                _emit_kv(key="LOOP_STATUS", value="zero-findings-degraded-panel")
                # #5210: emit round provenance on the terminal degraded-panel stdout
                # path too, mirroring the durable .step3-review-result.env write above,
                # so the Step 5c overlay never reconstructs rounds=0 from this envelope.
                _emit_kv(key="ROUNDS_COMPLETED", value=round_num)
                _emit_kv(key="REVIEW_ROUND_COUNT", value=round_num)
                for key in (
                    "PANEL_PRUNED_EMPTY",
                    "TALLY_PLAN_REVIEW_STATUS",
                    "ACCEPTED_COUNT",
                    "DEGRADED_PANEL",
                    "DEGRADED_PANEL_WARNING",
                    "INVALID_SLOT_PANEL_WARNING",
                    "REASON",
                ):
                    if degraded_values.get(key):
                        _emit_kv(key=key, value=degraded_values[key])
                return 0
            complete_values = dict(degraded_values)
            complete_values.update({k: v for k, v in cont.items() if k in {"PLAN_REVIEW_CONTINUE_REASON", "ACCEPTED_COUNT", "DEGRADED_PANEL", "DEGRADED_PANEL_WARNING", "INVALID_SLOT_PANEL_WARNING"}})
            step3_loop_write_completed_step3(tmpdir)
            _write_atomic(
                path=tmpdir / ".step3-review-cap.env",
                content=f"STEP3_REVIEW_CAP_REACHED=false\nSTEP3_REVIEW_ROUND_NUM={round_num}\n",
            )
            step3_loop_emit_envelope(tmpdir=tmpdir, status="complete", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=complete_values)
            if degraded_exit:
                # #5210: stdout must still carry degraded-panel LOOP_STATUS and round
                # provenance for normalizer/Step 5c overlay.
                _emit_kv(key="LOOP_STATUS", value="zero-findings-degraded-panel")
                _emit_kv(key="REVIEW_ROUND_COUNT", value=round_num)
            return 0

        step3_loop_emit_envelope(tmpdir=tmpdir, status="postplan-failed", round_num=round_num, rounds_completed=round_num, final_round=round_num, values={"REASON": f"invalid-phase:{phase or 'missing'}"})
        return 2


def run_step3_loop(argv: Sequence[str]) -> int:
    return run_step3_review(argv)


def prelaunch_failure(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review prelaunch-failure")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--reason", default="panel-init-failed")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    values = {"REASON": ns.reason, "LOOP_STATUS": "panel-init-failed"}
    _ = stage_panel_init_failed(design_tmpdir=tmpdir, trigger=ns.reason)
    step3_loop_emit_envelope(tmpdir=tmpdir, status="panel-init-failed", round_num=0, rounds_completed=0, final_round=0, values=values)
    return 0


def step35(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review step35")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    ns, _extra = parser.parse_known_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    result = _read_kv_file(path=tmpdir / ".step3-review-result.env")
    loop_status = result.get("LOOP_STATUS", os.environ.get("LOOP_STATUS", ""))
    step3_status = result.get("STEP3_REVIEW_LOOP_STATUS", os.environ.get("STEP3_REVIEW_LOOP_STATUS", ""))
    if step3_status in {"main-agent-apply-required", "per-round-approval-required", "postplan-operator-required"} or (
        not step3_status and loop_status in {"complete", "zero-findings-degraded-panel", "main-agent-vote-required"}
    ):
        step3_wrapper_write_completed_step3_only(tmpdir)
    _emit_kv(key="APPROVE_REQUESTED", value="true" if _read_bool_param(tmpdir=tmpdir, key="approve_requested", default=False) else "false")
    return 0


def step35_settle(argv: Sequence[str]) -> int:
    script = _plugin_root() / "skills" / "design" / "scripts" / "design-step35-settle.sh"
    bash = shutil.which("bash") or "/bin/bash"
    proc = subprocess.run([bash, str(script), *argv], cwd=str(_REPO_ROOT), check=False)
    return proc.returncode


def _delegate_step3_script(*, script_name: str, argv: Sequence[str]) -> int:
    script = _plugin_root() / "skills" / "design" / "scripts" / script_name
    if not script.is_file():
        return 2
    bash = shutil.which("bash") or "/bin/bash"
    return subprocess.run([bash, str(script), *argv], cwd=str(_REPO_ROOT), check=False).returncode


def _json_get_bool_cli(argv: Sequence[str]) -> int:
    return design_json_get_bool_main(argv)


def round_artifact_included(name: str) -> bool:
    if name in {"round-summary.env", "findings-classification.tsv", "prune-decision.env", "prune-nit.env", "reviewer-status.tsv"}:
        return True
    if name.endswith(("-vote-output.txt", "-vote-output-first-pass.txt", ".failure-diag")):
        return os.environ.get("LARCH_FLUSH_DEBUG") == "1"
    return False


def round_revise_artifact_included(_name: str) -> bool:
    return False


def round_revise_artifact_excluded(name: str) -> bool:
    suffixes = (
        "-output.txt",
        "-output-candidate.patch",
        ".done",
        ".dirty-tree",
        ".meta",
        ".prompt",
        ".sidecar",
        ".sidecar.history",
        ".events.jsonl",
        ".events.history",
        ".untracked-baseline",
        ".diag",
        ".failure-diag",
        ".json",
        ".stderr",
        ".token-record",
        ".stderr-tail",
    )
    return name in {"revise.env", "prompt.txt"} or any(name.endswith(suffix) for suffix in suffixes)


def drift_baseline_write_once(*, design_tmpdir: str | Path, plan_lines: str, diff_lines: str) -> int:
    ok, _message, tmpdir = _validate_tmpdir_arg(design_tmpdir)
    if not ok:
        return 1
    if not re.fullmatch(r"[0-9]+", plan_lines) or not re.fullmatch(r"[0-9]+", diff_lines):
        return 1
    path = tmpdir / "drift-baseline.env"
    if path.is_file() and not path.is_symlink():
        return 0
    if path.is_symlink():
        path.unlink()
    try:
        _write_atomic(path=path, content=f"BASELINE_PLAN_LINES={plan_lines}\nBASELINE_DIFF_LINES={diff_lines}\n")
    except OSError:
        return 1
    return 0


def _artifact_cli(*, argv: Sequence[str], predicate: Callable[[str], bool]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review round-artifact-included")
    parser.add_argument("name", nargs="?")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--name", dest="name_opt")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    name = ns.name_opt or ns.name
    if not name:
        parser.error("artifact name is required")
    return 0 if predicate(Path(name).name) else 1


def _drift_baseline_cli(argv: Sequence[str]) -> int:
    if not argv or argv[0] != "write-once":
        print("usage: cli.py plan-review drift-baseline write-once --design-tmpdir DIR --plan-lines N --diff-lines N", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog="cli.py plan-review drift-baseline write-once")
    parser.add_argument("write_once")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--plan-lines", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--diff-lines", required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    return drift_baseline_write_once(design_tmpdir=ns.design_tmpdir, plan_lines=ns.plan_lines, diff_lines=ns.diff_lines)


def run_main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if "--record-report-evidence" in args:
        idx = args.index("--record-report-evidence")
        try:
            status = args[idx + 1]
        except IndexError:
            print("plan-review run: --record-report-evidence requires a value", file=sys.stderr)
            return 2
        design_tmpdir: str | None = None
        if "--design-tmpdir" in args:
            didx = args.index("--design-tmpdir")
            if didx + 1 < len(args):
                design_tmpdir = args[didx + 1]
        return step3_record_report_evidence(status=status, design_tmpdir=design_tmpdir, cli_surface=True)
    return run_step3_review(args)


def tally_main(argv: list[str] | None = None) -> int:
    return tally_plan_review(argv or [])


def emit_main(argv: list[str] | None = None) -> int:
    return emit_plan(argv or [])


def finalize_main(argv: list[str] | None = None) -> int:
    return finalize_plan(argv or [])


def preview_main(argv: list[str] | None = None) -> int:
    return emit_design_plan_preview(argv or [])


def gate_b_counts_main(argv: list[str] | None = None) -> int:
    return gate_b_counts(argv or [])


def gate_b_finding_line_main(argv: list[str] | None = None) -> int:
    return gate_b_finding_line(argv or [])


def gate_b_dedup_main(argv: list[str] | None = None) -> int:
    return gate_b_dedup_plan(argv or [])


def persist_retally_env_main(argv: list[str] | None = None) -> int:
    return persist_retally_step3_env(argv or [])


def step3_state_main(argv: list[str] | None = None) -> int:
    return step3_state(argv or [])


def record_round_timing_main(argv: list[str] | None = None) -> int:
    return record_plan_review_round_timing(argv or [])


def persist_round_start_s_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review persist-round-start-s")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--round-num", type=int, required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--start-s", type=int, required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(argv or [])
    return persist_design_round_start_s(design_tmpdir=ns.design_tmpdir, round_num=ns.round_num, start_s=ns.start_s)


def continuation_main(argv: list[str] | None = None) -> int:
    return plan_review_continuation(argv or [])


def prelaunch_failure_main(argv: list[str] | None = None) -> int:
    return prelaunch_failure(argv or [])


def step35_main(argv: list[str] | None = None) -> int:
    return step35(argv or [])


def step35_settle_main(argv: list[str] | None = None) -> int:
    return step35_settle(argv or [])


def json_get_bool_main(argv: list[str] | None = None) -> int:
    return _json_get_bool_cli(argv or [])


def step3_entry_main(argv: list[str] | None = None) -> int:
    return step3_entry(argv or [])


def step3_entry(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review step3-entry")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--reentry", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns, _extra = parser.parse_known_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    if ns.reentry:
        (tmpdir / ".step3-reentry").touch()
    with contextlib.suppress(FileNotFoundError):
        (tmpdir / ".pause-save-complete").unlink()
    anchor = tmpdir / "plan-review-scope-anchor.txt"
    stripped = tmpdir / ".plan-review-scope-stripped.txt"
    issue_body = tmpdir / "issue-body.txt"
    feature = tmpdir / "feature-description.txt"
    if issue_body.is_file() and issue_body.stat().st_size > 0:
        proc = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan-block", "strip-body", "--file", str(issue_body), "--output", str(stripped)])
        if proc.returncode != 0:
            _ = prelaunch_failure(["--design-tmpdir", str(tmpdir), "--reason", "strip-body-failure"])
            return 1
    elif feature.is_file() and feature.stat().st_size > 0:
        proc = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan-block", "strip-body", "--file", str(feature), "--output", str(stripped)])
        if proc.returncode != 0:
            _ = prelaunch_failure(["--design-tmpdir", str(tmpdir), "--reason", "strip-body-failure"])
            return 1
    else:
        _write_atomic(path=stripped, content="")
    parts: list[str] = []
    if stripped.is_file():
        parts.append(stripped.read_text(encoding="utf-8", errors="replace"))
    outline = tmpdir / "design-outline.md"
    if outline.is_file() and (tmpdir / ".outline-approved").is_file():
        parts.append("\n\n## Approved direction (outline)\n\n" + outline.read_text(encoding="utf-8", errors="replace"))
    body = "".join(parts).strip()
    if not body:
        _ = prelaunch_failure(["--design-tmpdir", str(tmpdir), "--reason", "scope-anchor-missing"])
        return 1
    redact = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "redact", "secrets"], stdin_text=body)
    if redact.returncode != 0 or not redact.stdout.strip():
        _ = prelaunch_failure(["--design-tmpdir", str(tmpdir), "--reason", "scope-anchor-missing"])
        return 1
    _write_atomic(path=anchor, content=redact.stdout if redact.stdout.endswith("\n") else redact.stdout + "\n")
    _emit_kv(key="SCOPE_ANCHOR_FILE", value=str(anchor))
    return 0


def step3_mav_main(argv: list[str] | None = None) -> int:
    return _delegate_step3_script(script_name="design-step3-mav.sh", argv=argv or [])


def step3b_entry_main(argv: list[str] | None = None) -> int:
    return _delegate_step3_script(script_name="design-step3b-entry.sh", argv=argv or [])


def step3b_sanitize_main(argv: list[str] | None = None) -> int:
    return _delegate_step3_script(script_name="design-step3b-sanitize.sh", argv=argv or [])


def step3b_tail_main(argv: list[str] | None = None) -> int:
    return _delegate_step3_script(script_name="design-step3b-tail.sh", argv=argv or [])


def emit_rejected_main(argv: list[str] | None = None) -> int:
    return emit_rejected_findings(argv or [])


def round_artifact_included_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv=argv or [], predicate=round_artifact_included)


def round_revise_artifact_included_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv=argv or [], predicate=round_revise_artifact_included)


def round_revise_artifact_excluded_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv=argv or [], predicate=round_revise_artifact_excluded)


def drift_baseline_main(argv: list[str] | None = None) -> int:
    return _drift_baseline_cli(argv or [])
