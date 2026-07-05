"""Outcome normalization and issue-env normalization for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

from larch.state._tokens import (
    _DEFAULT_CLASSIFICATION_FILE,
    _issue_url_number,
    _read_state_file,
    _text_file_contains,
    _truthy,
    _validate_tmpdir_local_file,
    emit,
    read_kv,
    write_kvs,
)

_IN_FLIGHT_SHIP_PHASES = frozenset({"ci-initial", "rebase", "pr-create"})
_TERMINAL_MERGE_RESULTS = frozenset({"merged", "admin_merged", "already_merged"})
_STALE_FINALIZE_OUTCOME_KEYS = frozenset(
    {
        "STALL_TRACKING",
        "STALL_STEP",
        "PHASE",
        "BAIL_REASON",
        "IMPLEMENT_BAIL_REASON",
        "EXIT_CODE",
        "BAIL_NEEDS_USER_INPUT",
    }
)

_ISSUE_STDOUT_KEY_RE = re.compile(
    r"^(ISSUES_(CREATED|FAILED|DEDUPLICATED)|"
    r"ISSUE_(?:1_)?(FAILED|NUMBER|URL|DUPLICATE|DUPLICATE_OF_NUMBER|DUPLICATE_OF_URL))="
)
_ISSUE_STDOUT_KEY_LIKE_RE = re.compile(r"^[A-Z][A-Z0-9_]*=")


def _state_value(*, ship: Mapping[str, str], fin: Mapping[str, str], key: str) -> str:
    return ship.get(key) or fin.get(key, "")


def _is_nonzero_exit_code(value: str) -> bool:
    text = value.strip()
    if not text or text == "unknown":
        return False
    try:
        return int(text) != 0
    except ValueError:
        return False


def _has_failure_signals(
    *,
    ship: Mapping[str, str],
    fin: Mapping[str, str],
    bail_user: str,
) -> bool:
    """Return True when any explicit failure/bail evidence is present in state files."""
    return bool(
        _state_value(ship=ship, fin=fin, key="BAIL_REASON").strip()
        or _state_value(ship=ship, fin=fin, key="IMPLEMENT_BAIL_REASON").strip()
        or _is_nonzero_exit_code(_state_value(ship=ship, fin=fin, key="EXIT_CODE"))
        or _truthy(bail_user)
    )



def _has_clean_ship_recovery_evidence(ship: Mapping[str, str]) -> bool:
    pr_number = ship.get("PR_NUMBER", "").strip()
    pr_url = ship.get("PR_URL", "").strip()
    merge_result = ship.get("MERGE_RESULT", "").strip()
    has_ship_success_evidence = bool(
        (pr_number and pr_number != "0")
        or (pr_url and pr_url != "N/A")
        or merge_result in _TERMINAL_MERGE_RESULTS
    )
    if not has_ship_success_evidence:
        return False
    if ship.get("PHASE", "").strip() == "stalled":
        return False
    return not bool(
        ship.get("BAIL_REASON", "").strip()
        or ship.get("IMPLEMENT_BAIL_REASON", "").strip()
        or _is_nonzero_exit_code(ship.get("EXIT_CODE", ""))
    )


def _finalize_contains_stall_overlay(fin: Mapping[str, str]) -> bool:
    return bool(
        _truthy(fin.get("STALL_TRACKING", "false"))
        or fin.get("STALL_STEP", "").strip()
        or fin.get("PHASE", "").strip() == "stalled"
        or fin.get("BAIL_REASON", "").strip()
        or fin.get("IMPLEMENT_BAIL_REASON", "").strip()
        or _is_nonzero_exit_code(fin.get("EXIT_CODE", ""))
        or _truthy(fin.get("BAIL_NEEDS_USER_INPUT", "false"))
    )


def _finalize_stall_overlay_is_stale_after_recovery(
    *, ship: Mapping[str, str], fin: Mapping[str, str]
) -> bool:
    """Return True when finalize terminal-stall fields predate later clean ship state."""
    return _finalize_contains_stall_overlay(fin) and _has_clean_ship_recovery_evidence(ship)


def _effective_finalize_for_outcome(
    *, ship: Mapping[str, str], fin: Mapping[str, str]
) -> Mapping[str, str]:
    if not _finalize_stall_overlay_is_stale_after_recovery(ship=ship, fin=fin):
        return fin
    # Only outcome-choice fields from the stale terminal overlay are cleared.
    # Raw finalize values are still emitted below as diagnostics.
    effective = dict(fin)
    for key in _STALE_FINALIZE_OUTCOME_KEYS:
        effective[key] = ""
    return effective


def _has_pr_evidence(*, ship: Mapping[str, str], fin: Mapping[str, str]) -> bool:
    pr_number = (ship.get("PR_NUMBER") or fin.get("PR_NUMBER") or "").strip()
    if pr_number and pr_number != "0":
        return True
    pr_url = (ship.get("PR_URL") or fin.get("PR_URL") or "").strip()
    return bool(pr_url and pr_url != "N/A")


def _finalize_phase_is_stale_stall_overlay(
    *, ship: Mapping[str, str],
    fin: Mapping[str, str],
    any_stall: bool,
) -> bool:
    if any_stall:
        return False
    ship_phase = ship.get("PHASE", "").strip()
    fin_phase = fin.get("PHASE", "").strip()
    return fin_phase == "stalled" and ship_phase in _IN_FLIGHT_SHIP_PHASES


def _phase_counts_as_stalled(
    *, ship: Mapping[str, str],
    fin: Mapping[str, str],
    any_stall: bool,
) -> bool:
    ship_phase = ship.get("PHASE", "").strip()
    fin_phase = fin.get("PHASE", "").strip()
    if ship_phase == "stalled":
        return True
    if fin_phase != "stalled":
        return False
    return not _finalize_phase_is_stale_stall_overlay(ship=ship, fin=fin, any_stall=any_stall)


def _stall_signal_is_terminal(
    *, ship: Mapping[str, str],
    fin: Mapping[str, str],
    bail_user: str,
) -> bool:
    """Return True when a stall signal reflects a terminal stall worth the
    ``stalled`` label, rather than a stale flag a recovered run still carries.

    A committed in-flight snapshot (the Step-7a pre-ship flush or a during-ship log
    flush) can keep ``STALL_TRACKING=true`` from a mid-flight stall the run already
    recovered from; ``finalize-state.sh`` is absent there because it is written only
    on terminal outcomes. Honour the stall only on terminal evidence -- explicit
    failure/bail signals, a ship phase that is itself ``stalled``, or a written
    finalize state recording the stall -- so a progressing run is re-evaluated
    against its actual progress (merged / pr-created / shipping) instead of freezing
    the committed log at ``stalled``. Companion to the #5646 bailed catch-all guard
    and the #5169 stale finalize-PHASE overlay.
    """
    return bool(
        _has_failure_signals(ship=ship, fin=fin, bail_user=bail_user)
        or ship.get("PHASE", "").strip() == "stalled"
        or _truthy(fin.get("STALL_TRACKING", "false"))
    )


def _is_healthy_pre_terminal_pr_snapshot(*, ship: Mapping[str, str], fin: Mapping[str, str]) -> bool:
    if _state_value(ship=ship, fin=fin, key="BAIL_REASON").strip():
        return False
    if _state_value(ship=ship, fin=fin, key="IMPLEMENT_BAIL_REASON").strip():
        return False
    if _state_value(ship=ship, fin=fin, key="PHASE").strip() == "stalled":
        return False
    return not _is_nonzero_exit_code(_state_value(ship=ship, fin=fin, key="EXIT_CODE"))


def normalized_outcome_values(args: argparse.Namespace) -> dict[str, str]:
    tmpdir = Path(args.implement_tmpdir)
    ship = _read_state_file(tmpdir / "ship-pr-state.sh")
    fin = _read_state_file(tmpdir / "finalize-state.sh")
    fin_eff = _effective_finalize_for_outcome(ship=ship, fin=fin)
    ses = _read_state_file(tmpdir / "session-env.sh")
    seed = _read_state_file(tmpdir / "ship-seed-input.env")
    classification = _read_state_file(tmpdir / _DEFAULT_CLASSIFICATION_FILE)
    memory_stall = getattr(args, "in_memory_stall_tracking", "") or os.environ.get("STALL_TRACKING", "false")
    ship_stall = ship.get("STALL_TRACKING", "false")
    fin_stall = fin.get("STALL_TRACKING", "false")
    effective_fin_stall = fin_eff.get("STALL_TRACKING", "false")
    ses_stall = ses.get("STALL_TRACKING", "false")
    any_stall = _truthy(memory_stall) or _truthy(ship_stall) or _truthy(effective_fin_stall) or _truthy(ses_stall)
    phase_stalled = _phase_counts_as_stalled(ship=ship, fin=fin_eff, any_stall=any_stall)
    merge_result = ship.get("MERGE_RESULT") or fin_eff.get("MERGE_RESULT", "")
    merge = ship.get("MERGE") or fin_eff.get("MERGE", "")
    draft = ship.get("DRAFT") or fin_eff.get("DRAFT", "false")
    pr_number = ship.get("PR_NUMBER") or fin_eff.get("PR_NUMBER", "")
    forked = ship.get("FORKED_TARGET") or fin_eff.get("FORKED_TARGET") or ses.get("FORKED_TARGET", "false")
    ci_passed = ship.get("CI_PASSED") or fin_eff.get("CI_PASSED", "false")
    design_done = fin_eff.get("DESIGN_ONLY_DONE", "false")
    bail_user = fin_eff.get("BAIL_NEEDS_USER_INPUT", "false")

    if (any_stall or phase_stalled) and _stall_signal_is_terminal(
        ship=ship, fin=fin_eff, bail_user=bail_user
    ):
        outcome = "stalled"
    elif _truthy(forked):
        outcome = "forked-dry-run"
    elif _truthy(design_done):
        outcome = "design-only"
    elif merge_result in {"merged", "admin_merged"}:
        outcome = "merged"
    elif merge_result == "already_merged":
        outcome = "force-merged-externally"
    elif (
        _has_pr_evidence(ship=ship, fin=fin_eff)
        and not merge_result
        and _is_healthy_pre_terminal_pr_snapshot(ship=ship, fin=fin_eff)
        and not _truthy(bail_user)
    ):
        outcome = "pr-created-draft" if _truthy(draft) else "pr-created"
    elif (
        not _has_pr_evidence(ship=ship, fin=fin_eff)
        and not merge_result
        and not _has_failure_signals(ship=ship, fin=fin_eff, bail_user=bail_user)
    ):
        # Run is still in-flight (pre-PR committed snapshot); use a non-failure label
        # so the committed log does not misreport progressing runs as bailed.
        outcome = "shipping"
    else:
        outcome = "bailed"
    if _truthy(bail_user) and outcome == "bailed":
        outcome = "bailed-needs-user-input"
    succeeded = outcome in {"merged", "force-merged-externally", "pr-created", "pr-created-draft", "forked-dry-run"} and not any_stall
    merge_downgraded = (
        outcome == "pr-created"
        and _truthy(seed.get("MERGE", "false"))
        and not _truthy(merge)
        and classification.get("STALL_STEP") == "5"
        and classification.get("RESUME_HINT") == "step8-shippr"
        and _text_file_contains(path=tmpdir / "execution-issues.md", needle="panel-failed")
    )
    return {
        "IMPLEMENT_NORMALIZED_OUTCOME": outcome,
        "IMPLEMENT_OUTCOME_SUCCEEDED": "true" if succeeded else "false",
        "IMPLEMENT_MERGE_DOWNGRADED": "true" if merge_downgraded else "false",
        "IMPLEMENT_ANY_STALL_TRACKING": "true" if any_stall else "false",
        "IMPLEMENT_MEMORY_STALL_TRACKING": memory_stall or "false",
        "IMPLEMENT_SHIP_STALL_TRACKING": ship_stall or "false",
        "IMPLEMENT_FINALIZE_STALL_TRACKING": fin_stall or "false",
        "IMPLEMENT_SESSION_STALL_TRACKING": ses_stall or "false",
        "IMPLEMENT_MERGE_RESULT": merge_result,
        "IMPLEMENT_PR_NUMBER": pr_number,
        "IMPLEMENT_DRAFT": draft or "false",
        "IMPLEMENT_MERGE": merge,
        "IMPLEMENT_FORKED_TARGET": forked or "false",
        "IMPLEMENT_CI_PASSED": ci_passed or "false",
        "IMPLEMENT_DESIGN_ONLY_DONE": design_done or "false",
        "IMPLEMENT_BAIL_NEEDS_USER_INPUT": bail_user or "false",
    }


def normalize_outcome(args: argparse.Namespace) -> int:
    for key, value in normalized_outcome_values(args).items():
        emit(key=key, value=value)
    return 0


def _filter_issue_stdout(text: str) -> dict[str, str]:
    records: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.replace("\r", " ")
        if _ISSUE_STDOUT_KEY_RE.match(line):
            key, value = line.split("=", 1)
            records.append((key, value))
        elif records and not _ISSUE_STDOUT_KEY_LIKE_RE.match(line):
            key, value = records[-1]
            records[-1] = (key, value + " " + line)
    filtered: dict[str, str] = {}
    for key, value in records:
        filtered[key] = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    return filtered


def _issue_value_is_url(url: str) -> bool:
    return bool(re.match(r"https://github\.com/.+/.+/issues/\d+$", url or ""))


def normalize_issue_env(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    out = Path(args.issue_stdout_file)
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=out):
        print("stall-recovery: --issue-stdout-file outside implement tmpdir", file=sys.stderr)
        return 1
    env = tmpdir / "stall-recovery-issue.env"

    def fail(reason: str) -> int:
        with contextlib.suppress(OSError):
            env.unlink()
        emit(key="NORMALIZED", value="false")
        emit(key="REASON", value=reason)
        return 0

    if args.issue_exit_code is None:
        return fail("issue-exit-code-missing")
    exit_code = str(args.issue_exit_code)
    if not exit_code.isdigit():
        print("stall-recovery: --issue-exit-code must be a non-negative integer", file=sys.stderr)
        return 2
    if exit_code != "0":
        return fail("issue-exit-code")
    text = out.read_text(encoding="utf-8", errors="replace") if out.is_file() else ""
    filtered = _filter_issue_stdout(text)
    issues_failed = filtered.get("ISSUES_FAILED", "")
    if issues_failed != "0":
        if not issues_failed or not issues_failed.isdigit():
            return fail("issues-failed-invalid")
        return fail("issues-failed-nonzero")
    if _truthy(filtered.get("ISSUE_1_FAILED", "")):
        return fail("issue-1-failed")
    issue_number = filtered.get("ISSUE_1_NUMBER", "")
    issue_url = filtered.get("ISSUE_1_URL", "")
    duplicate = filtered.get("ISSUE_1_DUPLICATE", "") or filtered.get("ISSUE_DUPLICATE", "")
    duplicate_number = filtered.get("ISSUE_1_DUPLICATE_OF_NUMBER", "") or filtered.get("ISSUE_DUPLICATE_OF_NUMBER", "")
    duplicate_url = filtered.get("ISSUE_1_DUPLICATE_OF_URL", "") or filtered.get("ISSUE_DUPLICATE_OF_URL", "")
    if (
        (_truthy(duplicate) or not issue_number)
        and (_issue_value_is_url(duplicate_url) or not _issue_value_is_url(issue_url))
    ):
        issue_number = duplicate_number or (_issue_url_number(duplicate_url) or "")
        issue_url = duplicate_url
    if not issue_number or not issue_number.isdigit():
        return fail("issue-number-missing")
    if not _issue_value_is_url(issue_url):
        return fail("issue-url-missing")
    write_kvs(path=env, values={"ISSUE_NUMBER": issue_number, "ISSUE_URL": issue_url})
    emit(key="NORMALIZED", value="true")
    emit(key="ISSUE_NUMBER", value=issue_number)
    emit(key="ISSUE_URL", value=issue_url)
    return 0


def normalize_file_failure_report_env(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    if not tmpdir.is_dir():
        print("stall-recovery: --implement-tmpdir must exist", file=sys.stderr)
        return 1
    env_file = Path(args.file_failure_report_env)
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=env_file):
        print("stall-recovery: --file-failure-report-env invalid", file=sys.stderr)
        return 1
    status = read_kv(path=env_file, key="FILE_FAILURE_REPORT_STATUS")
    url = read_kv(path=env_file, key="FILE_FAILURE_REPORT_URL")
    reason = read_kv(path=env_file, key="FILE_FAILURE_REPORT_FALLBACK_REASON")
    allowed = {"filed", "dry-run", "dedup-comment", "no-match", "fallback-print-required", "lookup-failed-open"}
    if status not in allowed:
        status = "fallback-print-required"
        reason = reason or "helper-status-missing"
    emit(key="STALL_RECOVERY_REPORT_STATUS", value=status)
    if url:
        emit(key="STALL_RECOVERY_REPORT_URL", value=url)
        number = _issue_url_number(url)
        if number:
            emit(key="STALL_RECOVERY_REPORT_ISSUE_URL", value=url)
            emit(key="STALL_RECOVERY_REPORT_ISSUE_NUMBER", value=number)
    if reason:
        emit(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", value=reason)
    return 0
