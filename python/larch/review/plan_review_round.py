"""Native single-round /design plan-review body (ports plan-review-loop.sh)."""

from __future__ import annotations

import contextlib
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

from larch.agents import collect_results
from larch import io as larch_io
from larch.core import logging_util
from larch.review import review_aggregate
from larch.review import voting

_REPO_ROOT = Path(__file__).resolve().parents[3]
_COLLECT_TIMEOUT = "1860"
_PANEL_TIMEOUT = "1860"
_ARCHETYPES = ("arch", "innovation", "pragmatic", "requirements")
PER_REVIEWER_OOS_PROPOSAL_CAP = 3


def _plugin_root() -> Path:
    return Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or _REPO_ROOT)


def _emit(*, key: str, value: object = "") -> None:
    print(f"{key}={value}")


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    _ = merged.setdefault("CLAUDE_PLUGIN_ROOT", str(_plugin_root()))
    return subprocess.run(
        [sys.executable, str(_plugin_root() / "python" / "cli.py"), *argv],
        cwd=str(_REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
        env=merged,
    )


# (slot-name prefix, human-label prefix, nominal vendor). Order matters: the
# ``dyn-*`` prefixes must precede their bare forms. Shared by _slot_human_label
# and _nominal_vendor_from_slot so the vendor mapping cannot drift (issue #5838).
_SLOT_LABEL_PREFIXES = (
    ("dyn-cursor-plan-", "Cursor-dyn-", "cursor"),
    ("dyn-codex-plan-", "Codex-dyn-", "codex"),
    ("cursor-plan-", "Cursor-", "cursor"),
    ("codex-plan-", "Codex-", "codex"),
    ("codex-primary-plan-", "Codex-", "codex"),
)


def _slot_human_label(slot: str) -> str:
    for prefix, label, _ in _SLOT_LABEL_PREFIXES:
        if slot.startswith(prefix):
            return label + slot[len(prefix) :].replace("-", " ").title()
    return slot


def _nominal_vendor_from_slot(slot: str) -> str:
    """Vendor a plan-review slot was assigned to, from its name prefix.

    Empty when the slot has no vendor prefix (e.g. a generalist or Claude slot).
    """
    for prefix, _, vendor in _SLOT_LABEL_PREFIXES:
        if slot.startswith(prefix):
            return vendor
    return ""


def reconciled_reviewer_label(slot: str, *, executing_tool: str) -> str:
    """Human reviewer label, annotated ``(via <Tool>)`` on vendor fallback.

    On fallback the panel keeps the original slot name (e.g. ``cursor-plan-arch``)
    even though another tool produced the output, so attribution keyed on the slot
    label alone credits a vendor that contributed nothing. ``executing_tool`` is the
    collector ``TOOL=`` provenance for the slot's output file; when it names a known
    tool that differs from the slot's nominal vendor, annotate the label so the
    report reflects the tool that actually ran the slot (issue #5838).
    """
    label = _slot_human_label(slot)
    nominal = _nominal_vendor_from_slot(slot)
    tool = (executing_tool or "").strip()
    if nominal and tool and tool != "unknown" and tool != nominal:
        return f"{label} (via {tool.title()})"
    return label


def _load_manifest_slots(manifest: Path) -> list[str]:
    slots: list[str] = []
    for row in _iter_manifest_dict_rows(manifest):
        slot = str(row.get("slot") or "").strip()
        if slot:
            slots.append(slot)
    return slots


def _write_plan_review_prune_label_map(*, design: Path, manifest: Path) -> Path:
    label_map = design / "plan-review-prune-label-map.tsv"
    lines = [f"{slot}\t{_slot_human_label(slot)}" for slot in _load_manifest_slots(manifest)]
    _ = label_map.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return label_map


def _record_plan_review_prune_round(*, design: Path, round_num: int, manifest: Path, classification: Path) -> None:
    try:
        from larch.review import review_pipeline  # noqa: PLC0415

        label_map = _write_plan_review_prune_label_map(design=design, manifest=manifest)
        review_pipeline.reviewer_prune_record(
            ledger=design / "reviewer-prune-ledger.tsv",
            round_num=round_num,
            manifest=manifest,
            classification=classification,
            label_map=label_map
        )
    except Exception as exc:  # fail open by contract
        _emit(key="WARN", value=f"plan-review reviewer-prune record failed for round {round_num}: {exc}")


def _iter_manifest_dict_rows(manifest: Path) -> list[dict[str, object]]:
    if not manifest.is_file():
        return []
    lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
    return list(logging_util.iter_jsonl_dicts(lines))


def _compose_finding_block(
    slot: str,
    *,
    _scope: str,
    severity: str,
    focus: str,
    location: str,
    what: str,
    scenario: str,
    fix: str,
    finding_num: int | None = None,
    oos_num: int | None = None,
) -> str:
    if oos_num is not None:
        return (
            f"### OOS_{oos_num}: {what}\n"
            f"- **Description**: {what}. Scenario: {scenario}\n"
            f"- **Reviewer**: {slot}\n"
            f"- **Severity**: {severity or 'nit'}\n"
            f"- **Focus area**: {focus}\n"
            f"- **Location**: {location}\n"
            f"- **Phase**: design\n\n"
        )
    num = finding_num or 1
    return (
        f"### FINDING_{num}:\n"
        f"- **Reviewer(s)**: {slot}\n"
        f"- **Severity**: {severity or 'nit'}\n"
        f"- **Focus area**: {focus}\n"
        f"- **Location**: {location}\n"
        f"- **Concern**: {what}. Scenario: {scenario}\n"
        f"- **Proposed resolution**: {fix}\n\n"
    )


def _rows_from_structured(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    if path.suffix == ".jsonl":
        rows: list[dict[str, str]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append({str(k): str(v) for k, v in cast("dict[object, object]", obj).items()})
        return rows
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))
    except OSError:
        return []


def _is_oos_scope(scope: str) -> bool:
    return scope in {"out_of_scope", "out-of-scope", "oos"}


def _retain_oos_for_slot(oos_counts_by_slot: dict[str, int], *, slot_name: str) -> bool:
    retained_oos = oos_counts_by_slot.get(slot_name, 0)
    if retained_oos >= PER_REVIEWER_OOS_PROPOSAL_CAP:
        return False
    oos_counts_by_slot[slot_name] = retained_oos + 1
    return True


def _structured_finding_fields(row: dict[str, str]) -> tuple[str, str, str, str, str, str, str]:
    return (
        (row.get("scope") or "").strip().lower(),
        (row.get("severity") or "").strip(),
        (row.get("focus_area") or "").strip(),
        (row.get("location") or "").strip(),
        (row.get("what") or "").strip(),
        (row.get("scenario_or_breakage") or "").strip(),
        (row.get("suggested_fix") or "").strip(),
    )


def _log_reviewer_status_failure(*, design: Path, exc: OSError, tool: str) -> None:
    fail_log = design / "reviewer-status-write.failure.log"
    with contextlib.suppress(OSError):
        _ = fail_log.write_text(str(exc), encoding="utf-8")
    _ = _run_cli(
        argv=[
            "run-log",
            "append-failure",
            "--log",
            str(design / "execution-issues.md"),
            "--site",
            "design Step 3",
            "--tool",
            tool,
            "--exit-code",
            "1",
            "--category",
            "Warnings",
            "--output-file",
            str(fail_log),
            "--redact",
        ]
    )


def sync_latest_reviewer_status(*, design: Path, round_status: Path) -> None:
    """Copy per-round reviewer-status.tsv to latest-reviewer-status.tsv (#4848)."""
    latest = design / "latest-reviewer-status.tsv"
    if not round_status.is_file() or round_status.is_symlink():
        return
    if latest.is_symlink():
        return
    try:
        _ = shutil.copyfile(round_status, latest)
    except OSError as exc:
        _log_reviewer_status_failure(design=design, exc=exc, tool="sync_latest_reviewer_status")


def render_reviewer_status_table(status_tsv: Path) -> str | None:
    """Render the Step 3 chat-ready reviewer status table from a status TSV."""
    if not status_tsv.is_file() or status_tsv.is_symlink():
        return None
    status_icons = {
        "done": "✅",
        "pending": "⏳",
        "in-progress": "⏳",
        "failed": "❌",
        "timeout": "❌",
        "skipped": "⊘",
    }
    rows: list[str] = []
    try:
        with status_tsv.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = reader.fieldnames
            if not fieldnames or "slot" not in fieldnames or "status" not in fieldnames:
                return None
            for row in reader:
                slot = (row.get("slot") or "").strip()
                if not slot:
                    continue
                status = (row.get("status") or "").strip().lower()
                icon = status_icons.get(status, "❌")
                elapsed = (row.get("elapsed") or "").strip()
                suffix = f" {elapsed}" if elapsed and status != "skipped" else ""
                rows.append(f"{slot}: {icon}{suffix}")
    except OSError:
        return None
    if not rows:
        return None
    return f"📊 Reviewers: | {' | '.join(rows)} |"


def _stable_reviewer_status_table_path(design: Path) -> Path:
    return design / "reviewer-status-table.txt"


def _clear_reviewer_status_table(path: Path) -> None:
    if path.is_symlink():
        return
    with contextlib.suppress(OSError):
        if path.exists():
            path.unlink()


def _write_reviewer_status_table_artifacts(design: Path, *, source_tsv: Path, round_num: int) -> bool:
    table = render_reviewer_status_table(source_tsv)
    per_round = source_tsv.with_name("reviewer-status-table.txt")
    stable = _stable_reviewer_status_table_path(design)
    if table is None:
        _clear_reviewer_status_table(per_round)
        _clear_reviewer_status_table(stable)
        return False
    per_round_written = False
    stable_written = False
    try:
        if not source_tsv.parent.is_symlink() and not per_round.is_symlink():
            _ = per_round.write_text(f"{table}\n", encoding="utf-8")
            per_round_written = True
        if not stable.is_symlink():
            _clear_reviewer_status_table(stable)
            _ = stable.write_text(f"{table}\n", encoding="utf-8")
            stable_written = True
    except OSError as exc:
        if per_round_written or not per_round.is_symlink():
            _clear_reviewer_status_table(per_round)
        if stable_written or not stable.is_symlink():
            _clear_reviewer_status_table(stable)
        _log_reviewer_status_failure(design=design, exc=exc, tool="write_reviewer_status_table")
        return False
    _ = round_num
    return stable_written


def _bind_step3_review_round(design: Path) -> int | None:
    result_env = design / ".step3-review-result.env"
    if not result_env.is_file() or result_env.is_symlink():
        return None
    try:
        values = _parse_kv(result_env.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    for key in ("FINAL_ROUND_NUM", "STEP3_REVIEW_ROUND_NUM", "ROUNDS_COMPLETED"):
        value = (values.get(key) or "").strip()
        if value.isdigit():
            return int(value)
    return None


def materialize_stable_reviewer_status_table(design: Path, *, round_num: int | None = None) -> bool:
    stable = _stable_reviewer_status_table_path(design)
    if round_num is not None and stable.is_symlink():
        with contextlib.suppress(OSError):
            stable.unlink()
    bound_round = round_num if round_num is not None else _bind_step3_review_round(design)
    if bound_round is None:
        _clear_reviewer_status_table(stable)
        return False
    source = design / "plan-review" / f"round-{bound_round}" / "reviewer-status.tsv"
    if not source.is_file() or source.is_symlink() or source.parent.is_symlink():
        _clear_reviewer_status_table(stable)
        return False
    return _write_reviewer_status_table_artifacts(design=design, source_tsv=source, round_num=bound_round)


def _valid_manifest_slot_row(row: dict[str, object]) -> bool:
    slot = row.get("slot")
    tool = row.get("tool")
    output = row.get("output")
    agent = row.get("agent", "")
    prompt_file = row.get("prompt_file", "")
    if not isinstance(slot, str) or not slot:
        return False
    if not isinstance(tool, str) or tool not in {"codex", "cursor"}:
        return False
    if not isinstance(output, str) or not output:
        return False
    if "\n" in output or "\r" in output:
        return False
    if agent is None:
        agent = ""
    if prompt_file is None:
        prompt_file = ""
    if not isinstance(agent, str) or not isinstance(prompt_file, str):
        return False
    if agent and prompt_file:
        return False
    return bool(agent or prompt_file)


def _compose_findings_from_collector(
    *,
    design: Path,
    collect_text: str,
    manifest: Path,
) -> tuple[str, str, int, int]:
    """Return (in_scope_md, oos_md, ok_count, failure_count)."""
    manifest_slots = _load_manifest_slots(manifest)
    slot_by_output: dict[str, str] = {}
    for row in _iter_manifest_dict_rows(manifest):
        if not _valid_manifest_slot_row(row):
            continue
        output = str(row.get("output") or "")
        slot = str(row.get("slot") or "")
        if output and slot:
            slot_by_output[output] = slot

    findings_parts: list[str] = []
    ok_count = 0
    failure_count = 0
    finding_i = 1
    oos_i = 1
    oos_counts_by_slot: dict[str, int] = {}

    for record in collect_results.parse_collector_records(collect_text):
        rf = record.get("REVIEWER_FILE", "")
        tool = record.get("TOOL", "")
        status = record.get("STATUS", "")
        xc = record.get("EXIT_CODE", "")
        fr = record.get("FAILURE_REASON", "")
        sidecar = record.get("STRUCTURED_SIDECAR", "")
        slot_name = slot_by_output.get(rf, Path(rf).stem.replace("-output", ""))
        human = _slot_human_label(slot_name)
        if status != "OK":
            failure_count += 1
            fail_slug = re.sub(r"[^A-Za-z0-9._+-]+", "_", slot_name).strip("_")[:200] or "slot"
            fail_log = design / f"{fail_slug}-collector.failure.log"
            srec = f"REVIEWER_FILE={rf}|TOOL={tool}|STATUS={status}|EXIT_CODE={xc}|FAILURE_REASON={fr}"
            _ = _run_cli(
                argv=[
                    "agent",
                    "compose-collector-failure-log",
                    "--reviewer-file",
                    rf,
                    "--structured-record",
                    srec,
                    "--output",
                    str(fail_log),
                ]
            )
            _ = _run_cli(
                argv=[
                    "run-log",
                    "append-failure",
                    "--log",
                    str(design / "execution-issues.md"),
                    "--site",
                    "design Step 3",
                    "--tool",
                    f"collect-results {tool} {status}",
                    "--exit-code",
                    xc or "1",
                    "--category",
                    "External Reviewer Issues",
                    "--output-file",
                    str(fail_log),
                    "--redact",
                ]
            )
            continue
        ok_count += 1
        structured = Path(sidecar) if sidecar and Path(sidecar).is_file() else Path(f"{rf}.tsv")
        if not structured.is_file():
            structured = Path(f"{rf}.jsonl")
        rows = _rows_from_structured(structured)
        for row in rows:
            scope, sev, focus, loc, what, scen, fix = _structured_finding_fields(row)
            if _is_oos_scope(scope):
                if not _retain_oos_for_slot(oos_counts_by_slot=oos_counts_by_slot, slot_name=slot_name):
                    continue
                findings_parts.append(
                    _compose_finding_block(slot=human, _scope=scope, severity=sev, focus=focus, location=loc, what=what, scenario=scen, fix=fix, oos_num=oos_i)
                )
                oos_i += 1
            else:
                findings_parts.append(
                    _compose_finding_block(
                        slot=human,
                        _scope=scope,
                        severity=sev,
                        focus=focus,
                        location=loc,
                        what=what,
                        scenario=scen,
                        fix=fix,
                        finding_num=finding_i,
                    )
                )
                finding_i += 1

    _ = manifest_slots  # reserved for parity with bash slot manifest walk
    raw = "".join(findings_parts)
    fin = re.findall(r"(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)", raw)
    oos = re.findall(r"(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)", raw)
    in_scope = "\n\n".join(fin) + ("\n\n" if fin else "")
    oos_md = "\n\n".join(oos) + ("\n\n" if oos else "")
    return in_scope, oos_md, ok_count, failure_count


def write_reviewer_status_tsv(
    *,
    design: Path,
    round_num: int,
    collect_text: str | None = None,
) -> Path | None:
    """Materialize ``round-N/reviewer-status.tsv`` from the launched-slot manifest and
    collector records (issue #4848).

    The Step 3 post-notification flow reads the pre-rendered
    ``reviewer-status-table.txt`` that is derived from this TSV. ``latest`` remains
    a compatibility copy for existing consumers. This writes one row per launched
    slot as ``slot<TAB>status<TAB>elapsed`` (one header row, then one row per slot):

    - ``status`` is ``done`` when the collector recorded ``STATUS=OK`` for that slot's
      output file (the same ``OK`` predicate ``_compose_findings_from_collector`` uses),
      ``failed`` for any other collected status, and ``skipped`` when the slot produced
      no collector record.
    - ``elapsed`` is left blank: ``collect_results.CollectorRecord`` carries no
      per-reviewer duration, so per-slot elapsed is not currently captured.

    Returns the written path, or ``None`` when there is no valid launched slot.
    """
    manifest = design / "plan-review-slots.ndjson"
    slot_rows = [row for row in _iter_manifest_dict_rows(manifest) if _valid_manifest_slot_row(row)]
    if not slot_rows:
        return None
    status_by_output: dict[str, str] = {}
    status_by_norm_basename: dict[str, str] = {}
    tool_by_output: dict[str, str] = {}
    tool_by_norm_basename: dict[str, str] = {}
    if collect_text is not None:
        text = collect_text
    else:
        collector = design / "collector-results.env"
        text = collector.read_text(encoding="utf-8", errors="replace") if collector.is_file() and not collector.is_symlink() else ""
    if text:
        for record in collect_results.parse_collector_records(text):
            reviewer_file = record.get("REVIEWER_FILE", "")
            if reviewer_file:
                status = record.get("STATUS", "")
                tool = record.get("TOOL", "")
                status_by_output[reviewer_file] = status
                tool_by_output[reviewer_file] = tool
                norm = voting.normalize_reviewer_basename(reviewer_file)
                if status_by_norm_basename.get(norm) != "OK":
                    status_by_norm_basename[norm] = status
                    tool_by_norm_basename[norm] = tool
                with contextlib.suppress(OSError):
                    resolved = os.path.realpath(reviewer_file)
                    if resolved != reviewer_file:
                        status_by_output[resolved] = status
                        tool_by_output[resolved] = tool
    round_dir = design / "plan-review" / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    out = round_dir / "reviewer-status.tsv"
    if out.is_symlink():
        return None
    lines = ["slot\tstatus\telapsed"]
    for row in slot_rows:
        slot = str(row.get("slot") or "")
        output = str(row.get("output") or "")
        norm = voting.normalize_reviewer_basename(output)
        raw_status = status_by_norm_basename.get(norm)
        if raw_status is None:
            raw_status = status_by_output.get(output)
        if raw_status is None:
            with contextlib.suppress(OSError):
                raw_status = status_by_output.get(os.path.realpath(output))
        if raw_status is not None:
            status = "done" if raw_status == "OK" else "failed"
        else:
            status = "skipped"
        executing_tool = tool_by_norm_basename.get(norm)
        if executing_tool is None:
            executing_tool = tool_by_output.get(output)
        if executing_tool is None:
            with contextlib.suppress(OSError):
                executing_tool = tool_by_output.get(os.path.realpath(output))
        lines.append(f"{reconciled_reviewer_label(slot, executing_tool=executing_tool or '')}\t{status}\t")
    _ = out.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    _ = _write_reviewer_status_table_artifacts(design=design, source_tsv=out, round_num=round_num)
    sync_latest_reviewer_status(design=design, round_status=out)
    return out


def _write_header_only_reviewer_status_fallback(*, design: Path, round_num: int) -> None:
    round_dir = design / "plan-review" / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    out = round_dir / "reviewer-status.tsv"
    if out.is_symlink():
        return
    _ = out.write_text("slot\tstatus\telapsed\n", encoding="utf-8")
    _ = _write_reviewer_status_table_artifacts(design=design, source_tsv=out, round_num=round_num)
    sync_latest_reviewer_status(design=design, round_status=out)


def try_write_reviewer_status_tsv(
    *,
    design: Path,
    round_num: int,
    collect_text: str | None = None,
    header_fallback: bool = False,
) -> Path | None:
    """Write reviewer-status.tsv, logging disk failures and optionally falling back to header-only."""
    try:
        wrote = write_reviewer_status_tsv(design=design, round_num=round_num, collect_text=collect_text)
    except OSError as exc:
        _log_reviewer_status_failure(design=design, exc=exc, tool="write_reviewer_status_tsv")
        wrote = None
    if wrote is None and header_fallback:
        try:
            _write_header_only_reviewer_status_fallback(design=design, round_num=round_num)
            candidate = design / "plan-review" / f"round-{round_num}" / "reviewer-status.tsv"
            wrote = candidate if candidate.is_file() and not candidate.is_symlink() else None
        except OSError as exc:
            _log_reviewer_status_failure(design=design, exc=exc, tool="write_reviewer_status_tsv header fallback")
            wrote = None
    if wrote is None:
        _clear_reviewer_status_table(_stable_reviewer_status_table_path(design))
    return wrote


def _reset_zero_findings_tally_artifacts(design: Path) -> str:
    """Clear stale tally artifacts before zero-findings short-circuit return (issue #5032)."""
    tally_file = design / "voting-tally.md"
    for artifact in (
        design / "accepted-plan-findings.md",
        design / "rejected-findings.md",
        design / "oos.md",
        design / "oos-accepted-design.md",
    ):
        _ = artifact.write_text("", encoding="utf-8")
    tally_text = (
        "# Plan Review Voting Tally\n\n"
        "**Zero findings: reviewers reported no actionable items; voting skipped.**\n\n"
        + voting.render_voter_agreement_and_severity_scoreboards([])
    )
    _ = tally_file.write_text(tally_text, encoding="utf-8")
    return str(tally_file)


def _write_round_summary(
    *,
    design: Path,
    round_num: int,
    loop_status: str,
    collect_ok: int,
    collect_fail: int,
    values: dict[str, str],
) -> None:
    round_dir = design / "plan-review" / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        ("LOOP_STATUS", loop_status),
        ("COLLECT_OK_COUNT", str(collect_ok)),
        ("COLLECT_FAILURE_COUNT", str(collect_fail)),
        ("TALLY_PLAN_REVIEW_STATUS", values.get("TALLY_PLAN_REVIEW_STATUS", "")),
        ("AGGREGATOR_STATUS", values.get("AGGREGATOR_STATUS", "")),
        ("ACCEPTED_COUNT", values.get("ACCEPTED_COUNT", "0")),
        ("DEGRADED_PANEL", values.get("DEGRADED_PANEL", "0")),
    ]
    content = "".join(f"{k}={v}\n" for k, v in rows if v)
    dest = round_dir / "round-summary.env"
    tmp = dest.with_name(f"{dest.name}.tmp.{os.getpid()}")
    _ = tmp.write_text(content, encoding="utf-8")
    _ = tmp.replace(dest)


def _compose_attributed_ballot(*, design: Path, oos_md: str) -> str:
    in_scope_path = design / "findings-in-scope.md"
    in_scope = in_scope_path.read_text(encoding="utf-8", errors="replace") if in_scope_path.is_file() else ""
    parts = [part for part in (in_scope.strip(), oos_md.strip()) if part]
    return "\n\n".join(parts) + ("\n" if parts else "")


def _aggregation_ok_for_voting(agg_kv: dict[str, str], *, returncode: int = 0) -> bool:
    if returncode != 0:
        return False
    reason = agg_kv.get("REASON", "")
    if reason in {"insufficient-input", "disabled"}:
        return True
    if reason in {"dispatch-failed", "validation-failed", "validation-exhausted"}:
        return True
    return reason == "ok" and agg_kv.get("AGGREGATED", "false") == "true"


def _aggregator_status_from_kv(agg_kv: dict[str, str], *, returncode: int) -> str:
    if returncode != 0:
        return "aggregator-failed"
    reason = agg_kv.get("REASON", "")
    if reason == "ok" and agg_kv.get("AGGREGATED", "false") == "true":
        return "ok"
    if reason in {"insufficient-input", "disabled"}:
        return reason
    return reason or "aggregator-failed"


def _classify_round_loop_status(
    *,
    accepted: int,
    ok_count: int,
    degraded: bool,
    panel_pruned_empty: bool,
    tally_status: str,
) -> str:
    """Decide ``LOOP_STATUS`` for a completed (non-error) plan-review round.

    A zero-OK collector means no reviewer record parsed and no finding reached the
    ballot. When the panel was not pruned empty, that is always the loud
    ``degraded-empty-collector`` outcome, regardless of voter-dispatch health: a real
    empty collection must never be reported as a clean ``complete`` (issue #4790).
    """
    if accepted == 0 and ok_count == 0 and not panel_pruned_empty:
        return "degraded-empty-collector"
    if accepted == 0 and (degraded or tally_status == "skipped-empty-findings"):
        return "zero-findings-degraded-panel"
    return "complete"


# Issue #4996: the findings aggregator writes its forensics to stable top-level paths under the
# design tmpdir, and the Step 3 loop calls it once per round, so a later round's success overwrites
# the stderr/output a failed early round left behind. Mirror the diagnostic files into
# plan-review/round-N/ -- where reviewer forensics already live and the committed-log publish keeps
# them -- so an early-round aggregator failure stays diagnosable after a later round succeeds. The
# snapshot runs only on aggregator failure, so a clean run adds no committed bytes.
#
# Issue #5004: source the round-stamped basenames from review_aggregate so this snapshot set and the
# committed-pointer set cannot drift. They were hand-maintained in two modules and diverged, leaving the
# empty-merge/scope-parity/mv failure pointers resolving to clobbered top-level paths. Append the dispatch
# env and raw output for extra forensic context; those are snapshotted but never named by a committed pointer.
_AGGREGATOR_FORENSIC_FILES = (
    *sorted(review_aggregate.ROUND_STAMPED_FORENSICS),
    "aggregator-dispatch.env",
    "aggregator-output.txt",
)


def _snapshot_aggregator_forensics(*, design: Path, round_num: int) -> None:
    round_dir = design / "plan-review" / f"round-{round_num}"
    try:
        round_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    for name in _AGGREGATOR_FORENSIC_FILES:
        src = design / name
        if not src.is_file() or src.is_symlink():
            continue
        dst = round_dir / name
        if dst.is_symlink():
            continue
        with contextlib.suppress(OSError):
            _ = shutil.copyfile(src, dst)


def execute_round(
    design: Path,
    *,
    round_num: int,
    prune_round_num: int,
    codex_present: str,
    cursor_present: str,
    plan_file: Path,
    feature_file: Path,
) -> tuple[int, dict[str, str]]:
    """Run one plan-review round; return (exit_code, stdout_kv)."""
    values: dict[str, str] = {
        "PANEL_PRUNED_EMPTY": "false",
        "TALLY_PLAN_REVIEW_STATUS": "ok",
        "AGGREGATOR_STATUS": "ok",
        "ACCEPTED_COUNT": "0",
        "DEGRADED_PANEL": "0",
    }
    out_lines: list[str] = []

    panel_args = [
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--round-num",
        str(round_num),
        "--prune-round-num",
        str(prune_round_num),
        "--plan-file",
        str(plan_file),
        "--feature-file",
        str(feature_file),
        "--codex-present",
        codex_present,
        "--cursor-present",
        cursor_present,
        "--timeout",
        _PANEL_TIMEOUT,
    ]
    panel = _run_cli(argv=panel_args, env={"LARCH_QUIET_DISABLE": "1"})
    out_lines.append(panel.stdout)
    if panel.returncode != 0:
        # Do not swallow the panel dispatcher's stderr (issue #4747): re-surface it so
        # the real waterfall failure reaches operator-visible output instead of being
        # captured and dropped by _run_cli.
        if panel.stderr:
            print(panel.stderr, end="" if panel.stderr.endswith("\n") else "\n", file=sys.stderr)
        values.update(
            {
                "LOOP_STATUS": "panel-failed",
                "TALLY_PLAN_REVIEW_STATUS": "panel-failed",
                "AGGREGATOR_STATUS": "skipped",
                "DEGRADED_PANEL": "1",
            }
        )
        _ = try_write_reviewer_status_tsv(design=design, round_num=round_num, collect_text="", header_fallback=True)
        for k, v in values.items():
            _emit(key=k, value=v)
        return panel.returncode or 1, values

    panel_kv = _parse_kv(panel.stdout)
    values["PANEL_PRUNED_EMPTY"] = panel_kv.get("PANEL_PRUNED_EMPTY", "false")
    if panel_kv.get("INVALID_SLOT_PANEL_WARNING"):
        values["INVALID_SLOT_PANEL_WARNING"] = panel_kv["INVALID_SLOT_PANEL_WARNING"]
    elif panel_kv.get("DEGRADED_PANEL_WARNING"):
        values["INVALID_SLOT_PANEL_WARNING"] = panel_kv["DEGRADED_PANEL_WARNING"]
    if panel_kv.get("PANEL_PRUNED_EMPTY") == "true":
        values.update(
            {
                "LOOP_STATUS": "zero-findings-degraded-panel",
                "TALLY_PLAN_REVIEW_STATUS": "ok",
                "AGGREGATOR_STATUS": "skipped-pruned-empty",
                "ACCEPTED_COUNT": "0",
                "DEGRADED_PANEL": "0",
                "VOTING_TALLY_FILE": _reset_zero_findings_tally_artifacts(design),
            }
        )
        _write_round_summary(design=design, round_num=round_num, loop_status="zero-findings-degraded-panel", collect_ok=0, collect_fail=0, values=values)
        _ = try_write_reviewer_status_tsv(design=design, round_num=round_num, collect_text="", header_fallback=True)
        for k, v in values.items():
            _emit(key=k, value=v)
        return 0, values

    paths_file = panel_kv.get("PANEL_PATHS_FILE") or panel_kv.get("ALL_OUTPUT_FILES_PATH") or str(design / "plan-review-panel-paths.txt")
    paths_path = Path(paths_file)
    collect_out = ""
    collect_rc = 0
    if paths_path.is_file() and paths_path.stat().st_size > 0:
        collect = _run_cli(
            argv=[
                "agent",
                "collect-results",
                "--timeout",
                _COLLECT_TIMEOUT,
                "--substantive-validation",
                "--validation-mode",
                "--structured-reviewer-validation",
                "--paths-file",
                str(paths_path),
            ],
            env={"LARCH_QUIET_DISABLE": "1"},
        )
        collect_out = collect.stdout
        collect_rc = collect.returncode
        _ = (design / "collector-results.env").write_text(collect_out + ("\n" if collect_out and not collect_out.endswith("\n") else ""), encoding="utf-8")
    else:
        _ = (design / "collector-results.env").write_text("", encoding="utf-8")

    if collect_rc != 0 and not collect_results.parse_collector_records(collect_out):
        values.update(
            {
                "LOOP_STATUS": "panel-failed",
                "TALLY_PLAN_REVIEW_STATUS": "panel-failed",
                "AGGREGATOR_STATUS": "skipped",
                "DEGRADED_PANEL": "1",
            }
        )
        _ = try_write_reviewer_status_tsv(design=design, round_num=round_num, collect_text=collect_out)
        for k, v in values.items():
            _emit(key=k, value=v)
        return 1, values

    manifest = design / "plan-review-slots.ndjson"
    in_scope, oos_md, ok_count, fail_count = _compose_findings_from_collector(design=design, collect_text=collect_out, manifest=manifest)
    # Producer for the Step 3 post-notification reviewer-status table (#4848).
    # Written once here, after collection, so every post-collection terminal (success,
    # panel-failed, tally-error, main-agent-vote-required, degraded-empty-collector) has
    # the per-round TSV, stable table, and latest TSV compatibility copy in sync.
    _ = try_write_reviewer_status_tsv(design=design, round_num=round_num, collect_text=collect_out)
    _ = (design / "findings-in-scope.pre-dedup.md").write_text(in_scope, encoding="utf-8")
    _ = (design / "findings-oos.pre-dedup.md").write_text(oos_md, encoding="utf-8")
    _ = (design / "findings-oos.md").write_text(oos_md, encoding="utf-8")
    findings_path = design / "findings-in-scope.md"
    _ = findings_path.write_text(in_scope, encoding="utf-8")

    agg = _run_cli(
        argv=[
            "review",
            "aggregate-findings",
            "--findings-file",
            str(findings_path),
            "--review-tmpdir",
            str(design),
            "--codex-present",
            codex_present,
            "--cursor-present",
            cursor_present,
            "--mode",
            "description",
            "--input-mode",
            "plan",
            "--plan-file",
            str(plan_file),
            "--scope-anchor-file",
            str(design / "plan-review-scope-anchor.txt"),
            "--round-dir",
            str(design / "plan-review" / f"round-{round_num}"),
        ],
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    agg_kv = _parse_kv(agg.stdout)
    agg_status = _aggregator_status_from_kv(agg_kv=agg_kv, returncode=agg.returncode)
    values["AGGREGATOR_STATUS"] = agg_status
    # Retain this round's aggregator forensics before the next round overwrites the stable paths
    # (issue #4996). Only failures leave a committed pointer worth resolving, so skip the snapshot
    # for clean aggregations to avoid adding committed bytes on healthy runs.
    if agg_status not in {"ok", "insufficient-input", "disabled"}:
        _snapshot_aggregator_forensics(design=design, round_num=round_num)
    ballot = design / "ballot.txt"
    proposer_map = design / "proposer-map.tsv"
    if not _aggregation_ok_for_voting(agg_kv=agg_kv, returncode=agg.returncode):
        values.update(
            {
                "LOOP_STATUS": "panel-failed",
                "TALLY_PLAN_REVIEW_STATUS": "panel-failed",
                "DEGRADED_PANEL": "1",
            }
        )
        _write_round_summary(design=design, round_num=round_num, loop_status="panel-failed", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(key=k, value=v)
        return 1, values
    try:
        ballot_text = _compose_attributed_ballot(design=design, oos_md=oos_md)
        _ = ballot.write_text(ballot_text, encoding="utf-8")
        voting.write_proposer_map(ballot_file=ballot, map_file=proposer_map)
        _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=ballot_text), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"plan-review round: proposer map preparation failed: {exc}", file=sys.stderr)
        values.update(
            {
                "LOOP_STATUS": "tally-error",
                "TALLY_PLAN_REVIEW_STATUS": "tally-error",
                "DEGRADED_PANEL": "1",
            }
        )
        _write_round_summary(design=design, round_num=round_num, loop_status="tally-error", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(key=k, value=v)
        return 2, values

    # Issue #5032: when reviewers collected OK (ok_count > 0) but every one reported no
    # findings, the composed ballot has no FINDING_/OOS_ rows and there is nothing to vote
    # on. Short-circuit to the same benign zero-findings-degraded-panel outcome as the
    # PANEL_PRUNED_EMPTY branch instead of dispatching voters against an empty ballot:
    # empty-ballot voting inevitably degrades, and the voter-dispatch failure gate below
    # would otherwise map the converged round to panel-failed before the benign
    # _classify_round_loop_status could run. The ok_count == 0 empty-collection case is left
    # to the existing voter-dispatch / classifier path so its loud degraded-empty-collector
    # outcome (issue #4790) is preserved.
    if ok_count > 0 and fail_count == 0 and not re.search(r"(?m)^### (?:FINDING|OOS)_[0-9]+", ballot_text):
        values.update(
            {
                "LOOP_STATUS": "zero-findings-degraded-panel",
                "TALLY_PLAN_REVIEW_STATUS": "ok",
                "ACCEPTED_COUNT": "0",
                "DEGRADED_PANEL": "0",
                "VOTING_TALLY_FILE": _reset_zero_findings_tally_artifacts(design),
            }
        )
        values["REASON"] = values.get("REASON", "zero-findings-degraded-panel")
        values["ROUNDS_COMPLETED"] = str(round_num)
        _write_round_summary(
            design=design, round_num=round_num,
            loop_status="zero-findings-degraded-panel",
            collect_ok=ok_count,
            collect_fail=fail_count,
            values=values,
        )
        for k, v in values.items():
            _emit(key=k, value=v)
        return 0, values

    voter = _run_cli(
        argv=[
            "plan-review",
            "voter-dispatch",
            "--ballot-file",
            str(ballot),
            "--design-tmpdir",
            str(design),
            "--codex-available",
            codex_present,
            "--cursor-available",
            cursor_present,
        ],
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    out_lines.append(voter.stdout)
    voter_kv = _parse_kv(voter.stdout)
    if voter_kv.get("DEGRADED_PANEL_WARNING"):
        values["DEGRADED_PANEL_WARNING"] = voter_kv["DEGRADED_PANEL_WARNING"]
    if voter.returncode != 0 or voter_kv.get("DISPATCH_OK", "false") != "true":
        values.update(
            {
                "LOOP_STATUS": "panel-failed",
                "TALLY_PLAN_REVIEW_STATUS": "panel-failed",
                "DEGRADED_PANEL": "1",
            }
        )
        for k, v in values.items():
            _emit(key=k, value=v)
        return 1, values

    voter_args = [
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--design-tmpdir",
        str(design),
        "--proposer-map-file",
        str(proposer_map),
    ]
    for slot, key in (("1", "VOTER_1"), ("2", "VOTER_2"), ("3", "VOTER_3")):
        path = voter_kv.get(f"{key}_PATH", "")
        tool = voter_kv.get(f"{key}_TOOL", "")
        status = voter_kv.get(f"{key}_STATUS", "")
        if path and status != "failed":
            label = {"claude": "Claude", "codex": "Codex", "cursor": "Cursor"}.get(tool, tool)
            voter_args.extend(["--voter", f"{slot}:{label}:{path}"])

    classification = design / "plan-review" / f"round-{round_num}" / "findings-classification.tsv"
    classification.parent.mkdir(parents=True, exist_ok=True)
    voter_args.extend(["--findings-classification-out", str(classification)])

    tally = _run_cli(argv=voter_args, env={"LARCH_QUIET_DISABLE": "1"})
    out_lines.append(tally.stdout)
    tally_kv = _parse_kv(tally.stdout)
    values.update(tally_kv)
    tally_status = tally_kv.get("TALLY_PLAN_REVIEW_STATUS", "tally-error" if tally.returncode else "ok")

    if tally_status == "tally-error" or tally.returncode not in {0, 2}:
        values["LOOP_STATUS"] = "tally-error"
        values["TALLY_PLAN_REVIEW_STATUS"] = "tally-error"
        _write_round_summary(design=design, round_num=round_num, loop_status="tally-error", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(key=k, value=v)
        return 2, values

    if tally_status == "main-agent-vote-required":
        values["LOOP_STATUS"] = "main-agent-vote-required"
        _write_round_summary(design=design, round_num=round_num, loop_status="main-agent-vote-required", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(key=k, value=v)
        return 0, values

    accepted = len(re.findall(r"(?m)^### FINDING_[0-9]+:", (design / "accepted-plan-findings.md").read_text(encoding="utf-8", errors="replace") if (design / "accepted-plan-findings.md").is_file() else ""))
    values["ACCEPTED_COUNT"] = str(accepted)
    degraded = voter_kv.get("DISPATCH_OK", "true") != "true" or int(voter_kv.get("DEGRADED_PANEL", "0") or "0") == 1
    values["DEGRADED_PANEL"] = "1" if degraded else "0"

    loop_status = _classify_round_loop_status(
        accepted=accepted,
        ok_count=ok_count,
        degraded=degraded,
        panel_pruned_empty=values.get("PANEL_PRUNED_EMPTY") == "true",
        tally_status=tally_status,
    )
    if loop_status == "degraded-empty-collector":
        values["LOOP_STATUS"] = "degraded-empty-collector"
        values["DEGRADED_PANEL"] = "1"
        if classification.is_file():
            _record_plan_review_prune_round(design=design, round_num=round_num, manifest=manifest, classification=classification)
        _write_round_summary(design=design, round_num=round_num, loop_status="degraded-empty-collector", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(key=k, value=v)
        return 0, values

    values["LOOP_STATUS"] = loop_status
    if loop_status == "zero-findings-degraded-panel":
        values["REASON"] = values.get("REASON", "zero-findings-degraded-panel")

    values["ROUNDS_COMPLETED"] = str(round_num)
    _write_round_summary(design=design, round_num=round_num, loop_status=values["LOOP_STATUS"], collect_ok=ok_count, collect_fail=fail_count, values=values)
    if classification.is_file():
        _record_plan_review_prune_round(design=design, round_num=round_num, manifest=manifest, classification=classification)

    print("".join(out_lines), end="")
    for k, v in values.items():
        _emit(key=k, value=v)
    return 0, values
