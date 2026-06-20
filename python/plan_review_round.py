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

import collect_results
import logging_util
import voting

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COLLECT_TIMEOUT = "1860"
_PANEL_TIMEOUT = "1860"
_ARCHETYPES = ("arch", "innovation", "pragmatic", "requirements")


def _plugin_root() -> Path:
    return Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or _REPO_ROOT)


def _emit(key: str, value: object = "") -> None:
    print(f"{key}={value}")


def _parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


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


def _slot_human_label(slot: str) -> str:
    prefixes = (
        ("dyn-cursor-plan-", "Cursor-dyn-"),
        ("dyn-codex-plan-", "Codex-dyn-"),
        ("cursor-plan-", "Cursor-"),
        ("codex-plan-", "Codex-"),
        ("codex-primary-plan-", "Codex-"),
    )
    for prefix, label in prefixes:
        if slot.startswith(prefix):
            return label + slot[len(prefix) :].replace("-", " ").title()
    return slot


def _load_manifest_slots(manifest: Path) -> list[str]:
    slots: list[str] = []
    for row in _iter_manifest_dict_rows(manifest):
        slot = str(row.get("slot") or "").strip()
        if slot:
            slots.append(slot)
    return slots


def _write_plan_review_prune_label_map(design: Path, manifest: Path) -> Path:
    label_map = design / "plan-review-prune-label-map.tsv"
    lines = [f"{slot}\t{_slot_human_label(slot)}" for slot in _load_manifest_slots(manifest)]
    _ = label_map.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return label_map


def _record_plan_review_prune_round(design: Path, round_num: int, manifest: Path, classification: Path) -> None:
    try:
        import review_pipeline  # noqa: PLC0415

        label_map = _write_plan_review_prune_label_map(design, manifest)
        review_pipeline.reviewer_prune_record(
            design / "reviewer-prune-ledger.tsv",
            round_num,
            manifest,
            classification,
            label_map,
        )
    except Exception as exc:  # fail open by contract
        _emit("WARN", f"plan-review reviewer-prune record failed for round {round_num}: {exc}")


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


def _normalize_reviewer_output_basename(path: str) -> str:
    """Normalize retry and waterfall suffixes so manifest phase-1 paths match collector files."""
    base = Path(path).name
    if base.endswith(".txt"):
        stem, ext = base[:-4], ".txt"
    else:
        stem, ext = base, ""
    while True:
        for suffix in ("-phase2", "-phase3", "-retry"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        else:
            break
    return stem + ext


def sync_latest_reviewer_status(design: Path, round_status: Path) -> None:
    """Copy per-round reviewer-status.tsv to latest-reviewer-status.tsv (#4848)."""
    latest = design / "latest-reviewer-status.tsv"
    if not round_status.is_file() or round_status.is_symlink():
        return
    if latest.is_symlink():
        return
    with contextlib.suppress(OSError):
        _ = shutil.copyfile(round_status, latest)


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
                [
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
                [
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
            scope = (row.get("scope") or "").strip().lower()
            sev = (row.get("severity") or "").strip()
            focus = (row.get("focus_area") or "").strip()
            loc = (row.get("location") or "").strip()
            what = (row.get("what") or "").strip()
            scen = (row.get("scenario_or_breakage") or "").strip()
            fix = (row.get("suggested_fix") or "").strip()
            if scope in {"out_of_scope", "out-of-scope", "oos"}:
                findings_parts.append(
                    _compose_finding_block(human, _scope=scope, severity=sev, focus=focus, location=loc, what=what, scenario=scen, fix=fix, oos_num=oos_i)
                )
                oos_i += 1
            else:
                findings_parts.append(
                    _compose_finding_block(
                        human,
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


def write_reviewer_status_tsv(design: Path, round_num: int) -> Path | None:
    """Materialize ``round-N/reviewer-status.tsv`` from the launched-slot manifest and
    collector records (issue #4848).

    The SKILL.md Step 3 post-notification reviewer-status table reads
    ``latest-reviewer-status.tsv`` (or this per-round file as fallback), but nothing
    produced it: two sites only *copy* it to ``latest`` when it already exists, so
    neither file was ever created. This writes one row per launched slot as
    ``slot<TAB>status<TAB>elapsed`` (one header row, then one row per slot):

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
    collector = design / "collector-results.env"
    if collector.is_file() and not collector.is_symlink():
        text = collector.read_text(encoding="utf-8", errors="replace")
        for record in collect_results.parse_collector_records(text):
            reviewer_file = record.get("REVIEWER_FILE", "")
            if reviewer_file:
                status = record.get("STATUS", "")
                status_by_output[reviewer_file] = status
                status_by_norm_basename[_normalize_reviewer_output_basename(reviewer_file)] = status
                with contextlib.suppress(OSError):
                    resolved = os.path.realpath(reviewer_file)
                    if resolved != reviewer_file:
                        status_by_output[resolved] = status
    round_dir = design / "plan-review" / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    out = round_dir / "reviewer-status.tsv"
    if out.is_symlink():
        return None
    lines = ["slot\tstatus\telapsed"]
    for row in slot_rows:
        slot = str(row.get("slot") or "")
        output = str(row.get("output") or "")
        raw_status = status_by_output.get(output)
        if raw_status is None:
            raw_status = status_by_norm_basename.get(_normalize_reviewer_output_basename(output))
        if raw_status is None:
            with contextlib.suppress(OSError):
                raw_status = status_by_output.get(os.path.realpath(output))
        if raw_status is not None:
            status = "done" if raw_status == "OK" else "failed"
        else:
            status = "skipped"
        lines.append(f"{_slot_human_label(slot)}\t{status}\t")
    _ = out.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    sync_latest_reviewer_status(design, out)
    return out


def _write_round_summary(
    design: Path,
    round_num: int,
    *,
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


def _compose_attributed_ballot(design: Path, oos_md: str) -> str:
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
    panel = _run_cli(panel_args, env={"LARCH_QUIET_DISABLE": "1"})
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
        for k, v in values.items():
            _emit(k, v)
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
            }
        )
        _write_round_summary(design, round_num, loop_status="zero-findings-degraded-panel", collect_ok=0, collect_fail=0, values=values)
        for k, v in values.items():
            _emit(k, v)
        return 0, values

    paths_file = panel_kv.get("PANEL_PATHS_FILE") or panel_kv.get("ALL_OUTPUT_FILES_PATH") or str(design / "plan-review-panel-paths.txt")
    paths_path = Path(paths_file)
    collect_out = ""
    collect_rc = 0
    if paths_path.is_file() and paths_path.stat().st_size > 0:
        collect = _run_cli(
            [
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

    if collect_rc != 0 and not collect_results.parse_collector_records(collect_out):
        values.update(
            {
                "LOOP_STATUS": "panel-failed",
                "TALLY_PLAN_REVIEW_STATUS": "panel-failed",
                "AGGREGATOR_STATUS": "skipped",
                "DEGRADED_PANEL": "1",
            }
        )
        for k, v in values.items():
            _emit(k, v)
        return 1, values

    manifest = design / "plan-review-slots.ndjson"
    in_scope, oos_md, ok_count, fail_count = _compose_findings_from_collector(design, collect_out, manifest)
    # Producer for the SKILL.md Step 3 post-notification reviewer-status table (#4848).
    # Written once here, after collection, so every post-collection terminal (success,
    # panel-failed, tally-error, main-agent-vote-required, degraded-empty-collector) has
    # the per-round file and latest-reviewer-status.tsv stays in sync.
    with contextlib.suppress(OSError):
        _ = write_reviewer_status_tsv(design, round_num)
    _ = (design / "findings-in-scope.pre-dedup.md").write_text(in_scope, encoding="utf-8")
    _ = (design / "findings-oos.pre-dedup.md").write_text(oos_md, encoding="utf-8")
    _ = (design / "findings-oos.md").write_text(oos_md, encoding="utf-8")
    findings_path = design / "findings-in-scope.md"
    _ = findings_path.write_text(in_scope, encoding="utf-8")

    agg = _run_cli(
        [
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
        ],
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    agg_kv = _parse_kv(agg.stdout)
    agg_status = _aggregator_status_from_kv(agg_kv, returncode=agg.returncode)
    values["AGGREGATOR_STATUS"] = agg_status
    ballot = design / "ballot.txt"
    proposer_map = design / "proposer-map.tsv"
    if not _aggregation_ok_for_voting(agg_kv, returncode=agg.returncode):
        values.update(
            {
                "LOOP_STATUS": "panel-failed",
                "TALLY_PLAN_REVIEW_STATUS": "panel-failed",
                "DEGRADED_PANEL": "1",
            }
        )
        _write_round_summary(design, round_num, loop_status="panel-failed", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(k, v)
        return 1, values
    try:
        ballot_text = _compose_attributed_ballot(design, oos_md)
        _ = ballot.write_text(ballot_text, encoding="utf-8")
        voting.write_proposer_map(ballot, proposer_map)
        _ = ballot.write_text(voting.neutralize_reviewer_attribution(ballot_text), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"plan-review round: proposer map preparation failed: {exc}", file=sys.stderr)
        values.update(
            {
                "LOOP_STATUS": "tally-error",
                "TALLY_PLAN_REVIEW_STATUS": "tally-error",
                "DEGRADED_PANEL": "1",
            }
        )
        _write_round_summary(design, round_num, loop_status="tally-error", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(k, v)
        return 2, values

    voter = _run_cli(
        [
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
            _emit(k, v)
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

    tally = _run_cli(voter_args, env={"LARCH_QUIET_DISABLE": "1"})
    out_lines.append(tally.stdout)
    tally_kv = _parse_kv(tally.stdout)
    values.update(tally_kv)
    tally_status = tally_kv.get("TALLY_PLAN_REVIEW_STATUS", "tally-error" if tally.returncode else "ok")

    if tally_status == "tally-error" or tally.returncode not in {0, 2}:
        values["LOOP_STATUS"] = "tally-error"
        values["TALLY_PLAN_REVIEW_STATUS"] = "tally-error"
        _write_round_summary(design, round_num, loop_status="tally-error", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(k, v)
        return 2, values

    if tally_status == "main-agent-vote-required":
        values["LOOP_STATUS"] = "main-agent-vote-required"
        _write_round_summary(design, round_num, loop_status="main-agent-vote-required", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(k, v)
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
            _record_plan_review_prune_round(design, round_num, manifest, classification)
        _write_round_summary(design, round_num, loop_status="degraded-empty-collector", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(k, v)
        return 0, values

    values["LOOP_STATUS"] = loop_status
    if loop_status == "zero-findings-degraded-panel":
        values["REASON"] = values.get("REASON", "zero-findings-degraded-panel")

    values["ROUNDS_COMPLETED"] = str(round_num)
    _write_round_summary(design, round_num, loop_status=values["LOOP_STATUS"], collect_ok=ok_count, collect_fail=fail_count, values=values)
    if classification.is_file():
        _record_plan_review_prune_round(design, round_num, manifest, classification)

    print("".join(out_lines), end="")
    for k, v in values.items():
        _emit(k, v)
    return 0, values
