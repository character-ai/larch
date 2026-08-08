"""Slot-output binding for the Rust-owned waterfall dispatcher.

The dispatcher itself lives in `crates/larch-cli/src/waterfall_commands.rs`;
these cases cover only the Python reader the remaining panel consumers use.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.agents import slot_manifest


def _manifest(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    path: Path = tmp_path / "slots.ndjson"
    _ = path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    return path


def test_bind_manifest_slot_outputs_uses_slot_identity_for_compressed_success(tmp_path: Path) -> None:
    manifest: Path = _manifest(
        tmp_path,
        [
            {"slot": "voter-1", "tool": "cursor", "output": str(tmp_path / "v1.txt")},
            {"slot": "voter-2", "tool": "codex", "output": str(tmp_path / "v2.txt")},
            {"slot": "voter-3", "tool": "cursor", "output": str(tmp_path / "v3.txt")},
        ],
    )
    dropped: Path = tmp_path / "dropped-slots"
    _ = dropped.write_text("voter-1\tcursor\ttool-absent\tprimary tool cursor not present\n", encoding="utf-8")
    bindings: dict[str, slot_manifest.SlotOutputBinding] = slot_manifest.bind_manifest_slot_outputs(
        manifest_path=manifest,
        wf_kv={
            "ALL_OUTPUT_FILES": f"{tmp_path / 'v2.txt'} {tmp_path / 'v3-phase2.txt'}",
            "ALL_OUTPUT_TOOLS": "codex claude",
            "DROPPED_SLOTS_FILE": str(dropped),
        },
    )
    assert bindings["voter-1"] == slot_manifest.SlotOutputBinding(dropped=True)
    assert bindings["voter-2"] == slot_manifest.SlotOutputBinding(path=str(tmp_path / "v2.txt"), tool="codex")
    assert bindings["voter-3"] == slot_manifest.SlotOutputBinding(path=str(tmp_path / "v3-phase2.txt"), tool="claude")


def test_bind_manifest_slot_outputs_prefers_the_resolved_paths_file(tmp_path: Path) -> None:
    manifest: Path = _manifest(tmp_path, [{"slot": "s1", "tool": "codex", "output": str(tmp_path / "s1.txt")}])
    paths: Path = tmp_path / "paths.txt"
    _ = paths.write_text(f"{tmp_path / 's1-phase3.txt'}\n", encoding="utf-8")
    bindings: dict[str, slot_manifest.SlotOutputBinding] = slot_manifest.bind_manifest_slot_outputs(
        manifest_path=manifest,
        wf_kv={"ALL_OUTPUT_FILES_PATH": str(paths), "ALL_OUTPUT_FILES": "ignored.txt", "ALL_OUTPUT_TOOLS": "claude"},
    )
    assert bindings["s1"] == slot_manifest.SlotOutputBinding(path=str(tmp_path / "s1-phase3.txt"), tool="claude")


def test_bind_manifest_slot_outputs_falls_back_when_the_paths_file_is_unreadable(tmp_path: Path) -> None:
    manifest: Path = _manifest(tmp_path, [{"slot": "s1", "tool": "codex", "output": str(tmp_path / "s1.txt")}])
    bindings: dict[str, slot_manifest.SlotOutputBinding] = slot_manifest.bind_manifest_slot_outputs(
        manifest_path=manifest,
        wf_kv={
            "ALL_OUTPUT_FILES_PATH": str(tmp_path / "missing.txt"),
            "ALL_OUTPUT_FILES": str(tmp_path / "s1.txt"),
            "ALL_OUTPUT_TOOLS": "codex",
            "DROPPED_SLOTS_FILE": str(tmp_path / "missing-drops.txt"),
        },
    )
    assert bindings["s1"] == slot_manifest.SlotOutputBinding(path=str(tmp_path / "s1.txt"), tool="codex")


@pytest.mark.parametrize(
    "row",
    [
        {"tool": "codex", "output": "/tmp/out.txt"},
        {"slot": "", "tool": "codex", "output": "/tmp/out.txt"},
        {"slot": "s1", "tool": "claude", "output": "/tmp/out.txt"},
        {"slot": "s1", "tool": "codex", "output": ""},
        {"slot": "s1", "tool": "codex", "output": "/tmp/a\nb.txt"},
    ],
)
def test_load_slot_rows_rejects_malformed_rows(tmp_path: Path, row: dict[str, object]) -> None:
    manifest: Path = _manifest(tmp_path, [row])
    with pytest.raises(slot_manifest.ValidationError):
        _ = slot_manifest.load_slot_rows(manifest)


def test_load_slot_rows_rejects_an_empty_manifest(tmp_path: Path) -> None:
    manifest: Path = tmp_path / "empty.ndjson"
    _ = manifest.write_text("\n", encoding="utf-8")
    with pytest.raises(slot_manifest.ValidationError):
        _ = slot_manifest.load_slot_rows(manifest)


def test_load_slot_rows_rejects_non_object_rows(tmp_path: Path) -> None:
    manifest: Path = tmp_path / "bad.ndjson"
    _ = manifest.write_text("[]\nnot json\n", encoding="utf-8")
    with pytest.raises(slot_manifest.ValidationError):
        _ = slot_manifest.load_slot_rows(manifest)


@pytest.mark.parametrize(
    ("phase", "expected"),
    [("phase1", "/tmp/o.txt"), ("phase2", "/tmp/o-phase2.txt"), ("phase3", "/tmp/o-phase3.txt")],
)
def test_output_for_phase_matches_the_dispatcher_spelling(phase: str, expected: str) -> None:
    assert slot_manifest.output_for_phase(base="/tmp/o.txt", phase=phase) == expected


def test_output_for_phase_handles_a_suffixless_output() -> None:
    assert slot_manifest.output_for_phase(base="/tmp/o", phase="phase2") == "/tmp/o-phase2"
