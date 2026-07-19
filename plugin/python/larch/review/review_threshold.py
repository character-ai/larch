# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
# pylint: disable=too-many-branches,too-many-statements,too-many-locals,too-many-boolean-expressions
"""Check reviewer failure thresholds for the review pipeline."""

from __future__ import annotations

import re
from pathlib import Path

from larch.core import logging_util
from larch.review.review_pipeline_shared import (
    _collector_records,
    _emit_kv,
    _get,
    _get_list,
    _manifest_rows,
    _normalize_output_base,
    _parse_args,
)


def _is_static_reviewer_basename(base: str) -> bool:
    base = _normalize_output_base(base)
    return base == "codex-generalist-output.txt" or bool(re.match(r"^(?:cursor|codex)-specialist-.+-output\.txt$", base))


def _is_dynamic_reviewer_basename(base: str) -> bool:
    return bool(re.match(r"^dyn-.*-output(?:-phase[23]|-retry)*\.txt$", Path(base).name))


def _is_reviewer_output_basename(base: str) -> bool:
    base = _normalize_output_base(base)
    return _is_static_reviewer_basename(base) or _is_dynamic_reviewer_basename(base)


def _synthetic_dynamic_drop_key(*, slot: str, tool: str) -> str:
    return f"dyn-slot:{slot}:{tool}"


def _slot_tool_from_reviewer_basename(*, base: str, tool: str) -> tuple[str, str] | None:
    normalized = _normalize_output_base(base)
    if tool in {"codex", "cursor"}:
        dynamic = re.match(r"^(dyn-.+)-output(?:-phase[23]|-retry)*\.txt$", normalized)
        if dynamic:
            return dynamic.group(1), tool
        static = re.match(r"^(cursor|codex)-specialist-(.+)-output(?:-phase[23]|-retry)*\.txt$", normalized)
        if static:
            return static.group(2), static.group(1)
    return None


def _manifest_rows_by_slot_tool(manifest: Path | None) -> dict[tuple[str, str], str]:
    rows: dict[tuple[str, str], str] = {}
    if manifest is None or not manifest.is_file():
        return rows
    for row in _manifest_rows(manifest):
        slot = row.get("slot")
        tool = row.get("tool")
        output = row.get("output")
        if isinstance(slot, str) and isinstance(tool, str) and isinstance(output, str) and slot and tool and output:
            rows[(slot, tool)] = _normalize_output_base(Path(output).name)
    return rows


def _manifest_slot_tool_by_output(manifest: Path) -> dict[str, tuple[str, str]]:
    return {output: (slot, tool) for (slot, tool), output in _manifest_rows_by_slot_tool(manifest).items()}


def _dropped_slot_fields(line: str) -> tuple[str, str, str] | None:
    parts = [*line.split("\t"), "", "", ""]
    slot, tool, reason = parts[0], parts[1], parts[2]
    if not slot or tool not in {"codex", "cursor"}:
        return None
    return slot, tool, reason


def _dynamic_drop_output_base(*, slot: str, tool: str) -> str | None:
    if not slot.startswith("dyn-"):
        return None
    archetype = slot
    if tool == "codex" and archetype.endswith("-codex"):
        archetype = archetype.removesuffix("-codex")
    archetype = archetype.removeprefix("dyn-")
    suffix = "-codex-output.txt" if tool == "codex" else "-output.txt"
    return _normalize_output_base(f"dyn-{archetype}{suffix}")


def _dropped_reviewer_output_base(line: str, *, manifest: Path | None = None) -> str | None:
    fields = _dropped_slot_fields(line)
    if fields is None:
        return None
    slot, tool, reason = fields
    dynamic = slot.startswith("dyn-")
    if reason == "straggler-dropped" and not dynamic:
        return None
    manifest_output = _manifest_rows_by_slot_tool(manifest).get((slot, tool))
    if manifest_output:
        return manifest_output
    if dynamic:
        return _dynamic_drop_output_base(slot=slot, tool=tool)
    if slot == "generalist" and tool == "codex":
        return _normalize_output_base("codex-generalist-output.txt")
    return _normalize_output_base(f"{tool}-specialist-{slot}-output.txt")


def _output_file_success(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    # Match only a structured STATUS=NOT_SUBSTANTIVE declaration, not incidental
    # prose. A loose substring match false-positived when reviewers discussed the
    # NOT_SUBSTANTIVE concept in their findings, downgrading collector-OK slots to
    # ERROR (issue #4935). The collector remains the authoritative substantive
    # validator; this output-file check only flags an explicit self-declaration.
    return re.search(r"^STATUS=NOT_SUBSTANTIVE$", text, re.MULTILINE) is None


def check_reviewer_failure_threshold(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="review-check-reviewer-failure-threshold")
    usage = "Usage: review check-reviewer-failure-threshold --collector-results-file FILE --panel hard|simple [--intended-slots N] [--launched-slots N] [--dropped-slots-file FILE] [--panel-manifest FILE] [--reviewer-output-files FILE...] [--round-num N]"
    parsed = _parse_args(
        argv=argv,
        usage=usage,
        options={"--collector-results-file", "--panel", "--intended-slots", "--launched-slots", "--dropped-slots-file", "--panel-manifest", "--round-num"},
        list_options={"--reviewer-output-files"}
    )
    if parsed is None:
        return 0
    if not parsed:
        return 2
    panel = _get(parsed=parsed, key="--panel")
    if panel not in {"hard", "simple"}:
        logging_util.diagnostic("review check-reviewer-failure-threshold: --panel must be hard or simple")
        return 2
    intended_raw = _get(parsed=parsed, key="--intended-slots", default="3")
    round_raw = _get(parsed=parsed, key="--round-num", default="1")
    if not intended_raw.isdigit() or not round_raw.isdigit() or int(round_raw) <= 0:
        logging_util.diagnostic("review check-reviewer-failure-threshold: slot counts must be integers")
        return 2
    intended = int(intended_raw)
    succeeded = failed = counted = not_substantive = dropped_static = dropped_slots = dynamic_dropped_slots = 0
    statuses: dict[str, str] = {}
    dynamic_bases: set[str] = set()
    counted_slot_tools: set[tuple[str, str]] = set()
    manifest_raw = _get(parsed=parsed, key="--panel-manifest")
    manifest = Path(manifest_raw) if manifest_raw else None
    slot_tool_by_output = _manifest_slot_tool_by_output(manifest) if manifest and manifest.is_file() else {}

    def status_success(status: str) -> bool:
        return status in {"OK", "cap_hit"}

    def count_once(*, base: str, status: str, dynamic: bool = False) -> bool:
        nonlocal succeeded, failed, counted, not_substantive
        old = statuses.get(base)
        if old is None:
            statuses[base] = status
            if dynamic:
                dynamic_bases.add(base)
            counted += 1
            if status_success(status):
                succeeded += 1
            else:
                failed += 1
                if status == "NOT_SUBSTANTIVE":
                    not_substantive += 1
            return True
        if dynamic:
            dynamic_bases.add(base)
        return False

    collector = Path(_get(parsed=parsed, key="--collector-results-file"))
    for record in _collector_records(collector):
        reviewer_file = record.get("REVIEWER_FILE", "")
        status = record.get("STATUS", "")
        base = _normalize_output_base(Path(reviewer_file).name)
        if status and _is_reviewer_output_basename(base):
            slot_tool = slot_tool_by_output.get(base)
            if slot_tool:
                counted_slot_tools.add(slot_tool)
            else:
                derived = _slot_tool_from_reviewer_basename(base=base, tool=record.get("TOOL", ""))
                if derived:
                    counted_slot_tools.add(derived)
            count_once(base=base, status=status, dynamic=_is_dynamic_reviewer_basename(base) or (slot_tool[0].startswith("dyn-") if slot_tool else False))
    for item in _get_list(parsed=parsed, key="--reviewer-output-files"):
        path = Path(item)
        base = _normalize_output_base(path.name)
        if not _is_reviewer_output_basename(base):
            continue
        if base in statuses:
            continue
        slot_tool = slot_tool_by_output.get(base)
        if slot_tool:
            counted_slot_tools.add(slot_tool)
        count_once(base=base, status="OK" if _output_file_success(path) else "ERROR", dynamic=_is_dynamic_reviewer_basename(base) or (slot_tool[0].startswith("dyn-") if slot_tool else False))
    dropped_file_raw = _get(parsed=parsed, key="--dropped-slots-file")
    if dropped_file_raw:
        dropped_file = Path(dropped_file_raw)
        if not dropped_file.is_file():
            logging_util.diagnostic("review check-reviewer-failure-threshold: --dropped-slots-file must name a file")
            return 2
        for line in dropped_file.read_text(encoding="utf-8", errors="replace").splitlines():
            fields = _dropped_slot_fields(line)
            if fields is None:
                continue
            slot, tool, reason = fields
            dynamic_slot = slot.startswith("dyn-")
            base = _dropped_reviewer_output_base(line, manifest=manifest)
            if dynamic_slot:
                dynamic_dropped_slots += 1
            if base is not None:
                dropped_slots += 1
                if not dynamic_slot and reason != "straggler-dropped":
                    dropped_static += 1
                if base in statuses:
                    continue
                if count_once(base=base, status="ERROR", dynamic=dynamic_slot or _is_dynamic_reviewer_basename(base)):
                    counted_slot_tools.add((slot, tool))
                continue
            if not dynamic_slot:
                continue
            synthetic = _synthetic_dynamic_drop_key(slot=slot, tool=tool)
            drop_base = _dynamic_drop_output_base(slot=slot, tool=tool)
            if (
                (slot, tool) in counted_slot_tools
                or synthetic in statuses
                or (drop_base is not None and drop_base in statuses)
            ):
                continue
            if count_once(base=synthetic, status="ERROR", dynamic=True):
                counted_slot_tools.add((slot, tool))
    launched_raw = _get(parsed=parsed, key="--launched-slots")
    if launched_raw:
        if not launched_raw.isdigit():
            logging_util.diagnostic("review check-reviewer-failure-threshold: --launched-slots must be a non-negative integer")
            return 2
        never_launched = max(intended - int(launched_raw), 0)
        failed += max(never_launched - dropped_slots, 0)
    dynamic_failed_slots = sum(1 for base, status in statuses.items() if base in dynamic_bases and not status_success(status))
    threshold_ok = "true"
    threshold_reason = ""
    half_plus_one = intended // 2 + 1
    if failed >= half_plus_one:
        threshold_ok = "false"
        threshold_reason = f"{failed} of {intended} panel slots failed (threshold: >50% = >{intended // 2})"
    _emit_kv(key="INTENDED_SLOTS", value=intended)
    _emit_kv(key="SUCCEEDED_SLOTS", value=succeeded)
    _emit_kv(key="FAILED_SLOTS", value=failed)
    _emit_kv(key="COUNTED_SLOTS", value=counted)
    _emit_kv(key="NOT_SUBSTANTIVE_SLOTS", value=not_substantive)
    _emit_kv(key="DROPPED_SLOTS", value=dropped_slots)
    _emit_kv(key="DROPPED_STATIC_SLOTS", value=dropped_static)
    _emit_kv(key="DYNAMIC_FAILED_SLOTS", value=dynamic_failed_slots)
    _emit_kv(key="DYNAMIC_DROPPED_SLOTS", value=dynamic_dropped_slots)
    _emit_kv(key="THRESHOLD_OK", value=threshold_ok)
    _emit_kv(key="THRESHOLD_REASON", value=threshold_reason)
    return 0


def check_reviewer_failure_threshold_main(argv: list[str]) -> int:
    return check_reviewer_failure_threshold(argv)
