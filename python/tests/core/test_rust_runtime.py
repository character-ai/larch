"""Tests for thin Python consumers of Rust-owned commands."""

from __future__ import annotations

from larch.core.proc import CommandResult
from larch.core.rust_runtime import phantom_probe
from test_support import RecordingRunner


def test_phantom_probe_relays_validated_rust_envelope() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch", "git", "phantom-probe"),
                0,
                "PHANTOM_STATUS=phantom\nPHANTOM_COUNT=2\n",
                "→ phantom-probe: step-1\n",
                0.01,
            ),
        ],
    )

    result = phantom_probe(runner, step="step-1")

    assert result.lines == ("PHANTOM_STATUS=phantom", "PHANTOM_COUNT=2")
    assert runner.calls[0][-4:] == ["git", "phantom-probe", "--step", "step-1"]


def test_phantom_probe_fails_closed_for_missing_envelope() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("larch",), 127, "", "missing", 0.01)],
    )

    result = phantom_probe(runner, step="step-2")

    assert result.lines == ("PHANTOM_STATUS=unknown", "PHANTOM_REASON=phantom-probe-failed")
