"""Plan review loop: envelope persistence, plan emit/preview, step 3 state, round timing, continuation."""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from larch.design.design_lifecycle import json_get_bool, phase_driver_write_result_env
from larch.report.timing import TIMING_VENDOR_MIN_COLS, TimingLedger
from larch.review import plan_review_round
from larch.review import plan_review_tally
from larch.review.plan_review_common import (
    _REPO_ROOT,
    MERGE_KEYS,
    NON_NIT_CONTINUE_THRESHOLD,
    OPTIONAL_TRAILER_KEYS,
    POSTPLAN_EMIT_KEYS,
    STRUCTURAL_DIFF_LINE_THRESHOLD,
    STRUCTURAL_MIN_REVIEW_ROUNDS,
    STRUCTURAL_PLAN_LINE_THRESHOLD,
    _emit_kv,
    _plugin_root,
    _positive_int,
    _read_count,
    _read_kv_file,
    _require_tmpdir,
    _strip_crlf,
    _validate_tmpdir_arg,
    _write_atomic,
    effective_authorized_cap,
    plan_review_round_cap,
    resolve_plan_review_tier,
)
from larch.review.plan_review_findings import (
    _already_addressed_keys_in_rejected,
    _finding_dedup_key,
    _read_applied_finding_keys,
    _record_already_addressed_finding_keys,
    _record_applied_finding_keys,
)
from larch.review.plan_review_gate_b import (
    _STRUCTURED_GATE_B_SEVERITIES,
    _classify_gate_b_severity,
    _emit_gate_b_preview,
    _gate_b_display_rows,
    _parse_accepted_findings,
)
from larch.review.plan_review_normalize import (
    _step3_emit_next_action,
    _step3_next_action,
    _step3_next_action_rows,
    step3_loop_status_to_loop_status,
    step3_loop_write_completed_step3,
    step3_loop_write_terminal_step3,
    step3_record_report_evidence,
    step3_stage_postplan_failed,
)

DESIGN_ESCALATION_HIGH_ACCEPTED_THRESHOLD = 2


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


def _gate_b_prompt_line(row: object) -> str:
    finding_id = row.finding_id  # type: ignore[attr-defined]
    display_severity_label = row.display_severity_label  # type: ignore[attr-defined]
    reviewer_text = row.reviewer_text  # type: ignore[attr-defined]
    excerpt = row.excerpt  # type: ignore[attr-defined]
    prefix = f"FINDING_{finding_id} [{display_severity_label}]"
    if reviewer_text and excerpt:
        detail = f"{reviewer_text}: {excerpt}"
    elif reviewer_text:
        detail = reviewer_text
    else:
        detail = excerpt
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
        prior_round = _read_kv_file(path=env_path).get("ROUND_NUM", "")
        if prior_round and re.fullmatch(r"[0-9]+", prior_round):
            env_rows.append(("ROUND_NUM", prior_round))
        phase_driver_write_result_env(path=env_path, kvs=env_rows)
    _emit_kv(key="PERSIST_RETALLY_STATUS", value="ok")
    return 0


def _step3_clear_downstream_sentinels(tmpdir: Path) -> None:
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
        _step3_clear_downstream_sentinels(tmpdir)
        _step3_cleanup_settled_loop_state(tmpdir=tmpdir, max_round=count)
        state = "auto-continuation-entry"
    elif ns.gate_b_bypass:
        if (tmpdir / ".completed" / "step-3.5").exists():
            state = "refused-partial-gate-b-bypass"
        else:
            step3_loop_write_completed_step3(tmpdir)
            state = "gate-b-bypass"
    elif ns.direct_review_entry or ns.direct_review_pause_hygiene:
        action = "direct-review-entry" if ns.direct_review_entry else "direct-review-pause-hygiene"
        if not (tmpdir / ".step3-reentry").is_file():
            state = "noop"
        else:
            _step3_clear_downstream_sentinels(tmpdir)
            for name in ("step-1e", "step-2a", "step-2b", "step-2b.5"):
                (tmpdir / ".completed" / name).touch()
            if ns.direct_review_entry:
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
    """Append a canonical ``v1 round`` timing row for a design plan-review round."""
    ledger = tmpdir / "timing-ledger.tsv"
    round_s = str(round_num)
    if ledger.is_file():
        try:
            existing = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            existing = []
        for line in existing:
            cols = line.split("\t")
            if len(cols) >= 8 and cols[0] == "v1" and cols[1] == "round" and cols[3] == "design" and cols[5] == round_s:  # noqa: PLR2004
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


def _gate_b_apply_start_s(*, ledger: Path, round_start_s: int, end_s: int, output_basename: str) -> int | None:
    if not ledger.is_file():
        return None
    try:
        lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    latest_end_s: int | None = None
    duplicate = False
    for line in lines:
        cols = line.split("\t")
        if len(cols) < TIMING_VENDOR_MIN_COLS or cols[0] != "v1" or cols[1] != "vendor" or cols[3] != "design":
            continue
        kind = cols[6]
        if kind == "gate-b-apply" and Path(cols[10]).name == output_basename:
            duplicate = True
        if kind == "gate-b-apply":
            continue
        try:
            row_start_s = int(cols[7])
            row_end_s = int(cols[8])
        except ValueError:
            continue
        if row_end_s <= round_start_s or row_start_s >= end_s:
            continue
        latest_end_s = row_end_s if latest_end_s is None else max(latest_end_s, row_end_s)
    if duplicate or latest_end_s is None or latest_end_s >= end_s:
        return None
    return latest_end_s


def _record_gate_b_apply_timing_from_round_window(*, tmpdir: Path, round_num: int, end_s: int) -> None:
    """Record the Gate B apply/dedup/postplan span for a completed design round."""
    start_file = tmpdir / "plan-review" / f"round-{round_num}" / "round-start-s"
    try:
        round_start_s = int(start_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return
    if round_start_s <= 0 or end_s <= round_start_s:
        return
    ledger = tmpdir / "timing-ledger.tsv"
    output = f"gate-b-apply-round-{round_num}.out"
    gate_b_start_s = _gate_b_apply_start_s(
        ledger=ledger,
        round_start_s=round_start_s,
        end_s=end_s,
        output_basename=output,
    )
    if gate_b_start_s is None:
        return
    try:
        TimingLedger(path=ledger, skill="design").record_vendor_task(
            vendor="claude",
            task_kind="gate-b-apply",
            start_s=gate_b_start_s,
            end_s=end_s,
            output=output,
            status="complete",
        )
    except (OSError, ValueError):
        return


def _record_design_round_timing_from_start_file(*, tmpdir: Path, round_num: int, end_s: int | None = None) -> None:
    """Record canonical per-round timing for a completed design plan-review round."""
    start_file = tmpdir / "plan-review" / f"round-{round_num}" / "round-start-s"
    try:
        start_s = int(start_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return
    if start_s <= 0:
        return
    round_end_s = int(time.time()) if end_s is None else end_s
    _append_canonical_round_timing(tmpdir=tmpdir, round_num=round_num, start_s=start_s, end_s=round_end_s)


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
    cap = effective_authorized_cap(tmpdir)
    panel_tier = ""
    if high >= DESIGN_ESCALATION_HIGH_ACCEPTED_THRESHOLD and high_new > 0 and review_count < plan_review_round_cap("HARD"):
        cont = True
        resolution = resolve_plan_review_tier(tmpdir)
        from larch.calibration import difficulty  # noqa: PLC0415
        if resolution.panel_tier != difficulty.HARD:
            reason = "escalated-high-accepted"
            difficulty.append_escalation(tmpdir / difficulty.DIFFICULTY_RECORD_BASENAME, review_count + 1, resolution.panel_tier, difficulty.HARD, reason)
        else:
            reason = "high-accepted"
        cap = plan_review_round_cap("HARD")
        panel_tier = difficulty.HARD
    elif review_count >= cap:
        reason = "cap-reached"
    elif panel_pruned_empty == "true":
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
        ("REVIEW_ROUND_CAP", str(cap)),
        ("PANEL_TIER", panel_tier),
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


# pyright: reportPrivateUsage=false, reportUnknownVariableType=false, reportUnusedFunction=false
