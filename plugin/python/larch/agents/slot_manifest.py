"""Bind waterfall outputs back to the slot manifest that produced them.

The three-phase dispatcher itself is Rust-owned (`agent dispatch-waterfall`).
What stays here is the reader every remaining Python panel consumer needs: given
one slot manifest and the dispatcher's stdout key-values, say which output file
each named slot ended with and which slots were dropped. Position in the
compressed `ALL_OUTPUT_FILES` list is not slot identity, so the binding matches
on the manifest's own output path across all three phase spellings.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

PHASES = ("phase1", "phase2", "phase3")


class ValidationError(RuntimeError):
    """A manifest row that does not satisfy the slot-row contract."""


@dataclass(frozen=True)
class SlotRow:
    """One manifest row, reduced to the fields output binding reads."""

    name: str
    tool: str
    output: str


@dataclass(frozen=True)
class SlotOutputBinding:
    """Where one named slot's result landed, or why it has none."""

    path: str = ""
    tool: str = ""
    dropped: bool = False


def _parse_slot_row(row: str) -> SlotRow:
    try:
        data: object = json.loads(row)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"slot manifest: invalid slot row: {row}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"slot manifest: invalid slot row: {row}")
    data_dict = cast("dict[str, object]", data)
    name: object | None = data_dict.get("slot")
    tool: object | None = data_dict.get("tool")
    output: object | None = data_dict.get("output")
    if not isinstance(name, str) or not name:
        raise ValidationError(f"slot manifest: invalid slot row: {row}")
    if not isinstance(tool, str) or tool not in {"codex", "cursor"}:
        raise ValidationError(f"slot manifest: invalid slot row: {row}")
    if not isinstance(output, str) or not output or "\n" in output or "\r" in output:
        raise ValidationError(f"slot manifest: invalid slot row: {row}")
    return SlotRow(name=name, tool=tool, output=output)


def load_slot_rows(manifest_path: str | Path) -> list[SlotRow]:
    """Read every slot row from one manifest, rejecting malformed rows."""
    text: str = Path(manifest_path).read_text(encoding="utf-8", errors="replace")
    rows: list[SlotRow] = [_parse_slot_row(row) for row in text.splitlines() if row]
    if not rows:
        raise ValidationError("slot manifest: slots file contains no slot rows")
    return rows


def output_for_phase(*, base: str, phase: str) -> str:
    """Return the output path one phase writes for a slot's base output."""
    if phase == "phase1":
        return base
    if base.endswith(".txt"):
        return f"{base[:-4]}-{phase}.txt"
    return f"{base}-{phase}"


def _read_resolved_paths_from_kv(wf_kv: Mapping[str, str]) -> list[str]:
    path_file: str = wf_kv.get("ALL_OUTPUT_FILES_PATH", "")
    if path_file:
        try:
            text: str = Path(path_file).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        else:
            return [line for line in text.splitlines() if line]
    return [part for part in wf_kv.get("ALL_OUTPUT_FILES", "").split() if part]


def _read_dropped_slots(wf_kv: Mapping[str, str]) -> set[str]:
    path: str = wf_kv.get("DROPPED_SLOTS_FILE", "")
    if not path:
        return set()
    try:
        text: str = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {line.split("\t", 1)[0] for line in text.splitlines() if line}


def _phase_candidate_paths(output: str) -> set[str]:
    return {output_for_phase(base=output, phase=phase) for phase in PHASES}


def _path_matches_manifest_output(*, candidate: str, manifest_output: str) -> bool:
    candidates: set[str] = _phase_candidate_paths(manifest_output)
    if candidate in candidates:
        return True
    cand_name: str = Path(candidate).name
    return any(cand_name == Path(value).name for value in candidates)


def _match_index(*, row: SlotRow, resolved_paths: Sequence[str], bound: set[int]) -> int | None:
    for idx, path in enumerate(resolved_paths):
        if idx in bound:
            continue
        if _path_matches_manifest_output(candidate=path, manifest_output=row.output):
            return idx
    return None


def bind_manifest_slot_outputs(*, manifest_path: str | Path, wf_kv: Mapping[str, str]) -> dict[str, SlotOutputBinding]:
    """Bind waterfall outputs by manifest slot, not compressed stdout position."""
    resolved_paths: list[str] = _read_resolved_paths_from_kv(wf_kv)
    tools: list[str] = [part for part in wf_kv.get("ALL_OUTPUT_TOOLS", "").split() if part]
    dropped_slots: set[str] = _read_dropped_slots(wf_kv)
    rows: list[SlotRow] = load_slot_rows(manifest_path)
    bound_indexes: set[int] = set()
    bindings: dict[str, SlotOutputBinding] = {}
    for row in rows:
        match_index: int | None = _match_index(row=row, resolved_paths=resolved_paths, bound=bound_indexes)
        if match_index is None:
            bindings[row.name] = SlotOutputBinding(dropped=row.name in dropped_slots)
            continue
        bound_indexes.add(match_index)
        tool: str = tools[match_index] if match_index < len(tools) else ""
        bindings[row.name] = SlotOutputBinding(path=resolved_paths[match_index], tool=tool, dropped=False)
    return bindings
