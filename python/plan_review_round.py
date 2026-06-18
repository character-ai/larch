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
    if not manifest.is_file():
        return []
    slots: list[str] = []
    for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        slot = str(row.get("slot") or "").strip()
        if slot:
            slots.append(slot)
    return slots


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


def _compose_findings_from_collector(
    design: Path,
    collect_text: str,
    manifest: Path,
) -> tuple[str, str, int, int]:
    """Return (in_scope_md, oos_md, ok_count, failure_count)."""
    manifest_slots = _load_manifest_slots(manifest)
    slot_by_output: dict[str, str] = {}
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
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

    for line in collect_text.splitlines():
        if not line.strip() or "\x1f" not in line:
            continue
        rf, tool, status, xc, fr, sidecar = (line.split("\x1f") + [""] * 6)[:6]
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


def _rollback_round_count(design: Path, prior: int) -> None:
    path = design / "review-round-count.txt"
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    _ = tmp.write_text(f"{prior}\n", encoding="utf-8")
    _ = tmp.replace(path)


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
    prior_count = 0
    count_path = design / "review-round-count.txt"
    if count_path.is_file() and not count_path.is_symlink():
        raw = count_path.read_text(encoding="utf-8", errors="replace").strip()
        prior_count = int(raw, 10) if re.fullmatch(r"[0-9]+", raw) else 0

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

    if collect_rc != 0 and not any("\x1f" in line for line in collect_out.splitlines()):
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
    _ = (design / "findings-in-scope.pre-dedup.md").write_text(in_scope, encoding="utf-8")
    _ = (design / "findings-oos.pre-dedup.md").write_text(oos_md, encoding="utf-8")
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
    agg_status = "ok" if agg.returncode == 0 else "aggregator-failed"
    values["AGGREGATOR_STATUS"] = agg_status
    ballot = design / "ballot.txt"
    if ballot.is_file():
        ballot_text = ballot.read_text(encoding="utf-8", errors="replace")
    else:
        ballot_text = in_scope
        _ = ballot.write_text(ballot_text, encoding="utf-8")

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

    voter_args = ["plan-review", "tally", "--ballot-file", str(ballot), "--design-tmpdir", str(design)]
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
        _rollback_round_count(design, prior_count)
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

    if accepted == 0 and ok_count == 0 and degraded:
        values["LOOP_STATUS"] = "degraded-empty-collector"
        values["DEGRADED_PANEL"] = "1"
        _rollback_round_count(design, prior_count)
        _write_round_summary(design, round_num, loop_status="degraded-empty-collector", collect_ok=ok_count, collect_fail=fail_count, values=values)
        for k, v in values.items():
            _emit(k, v)
        return 0, values

    if accepted == 0 and (degraded or tally_status == "skipped-empty-findings"):
        values["LOOP_STATUS"] = "zero-findings-degraded-panel"
        values["REASON"] = values.get("REASON", "zero-findings-degraded-panel")
    else:
        values["LOOP_STATUS"] = "complete"

    values["ROUNDS_COMPLETED"] = str(round_num)
    _write_round_summary(design, round_num, loop_status=values["LOOP_STATUS"], collect_ok=ok_count, collect_fail=fail_count, values=values)
    round_status = design / "plan-review" / f"round-{round_num}" / "reviewer-status.tsv"
    latest = design / "latest-reviewer-status.tsv"
    if round_status.is_file() and not round_status.is_symlink():
        with contextlib.suppress(OSError):
            _ = shutil.copyfile(round_status, latest)

    print("".join(out_lines), end="")
    for k, v in values.items():
        _emit(k, v)
    return 0, values
