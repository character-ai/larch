"""Focused durable-state coverage for the debate orchestration boundary."""
from __future__ import annotations

import json
from pathlib import Path

from larch.debate import protocol
from larch.debate.orchestrator import ProposalState, TurnRequest, TurnResult, initialize, record_turn, round_prep


def _initialize(root: Path) -> ProposalState:
    return initialize(
        root=root,
        expected_fingerprint="ABSENT",
        repo_workdir=str(Path.cwd()),
        log_root=str(root / "logs"),
        run_id="test-run",
        point_universe=(protocol.PointId(1),),
        run_local_values={"run": "local"},
        cursor_present=True,
        codex_present=True,
        claude_present=False,
        restore_issue_number="1",
        restore_original_title="old",
        restore_title="new",
    )


def test_canonical_state_and_turn_progression(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    payload = json.loads((tmp_path / "debate-state.json").read_text(encoding="utf-8"))
    assert payload["fingerprint"] == state.fingerprint
    state = round_prep(root=tmp_path, expected_fingerprint=state.fingerprint, round_number=1)

    def runner(request: TurnRequest) -> TurnResult:
        output = request.output
        _ = output.write_text("POINT POINT_1 AGREE agreed", encoding="utf-8")
        return TurnResult(ok=True, output=output)

    state, error = record_turn(root=tmp_path, expected_fingerprint=state.fingerprint, round_number=1, slot="cursor", runner=runner)
    assert error == ""
    assert state.active_round is not None
    state, error = record_turn(root=tmp_path, expected_fingerprint=state.fingerprint, round_number=1, slot="codex", runner=runner)
    assert error == ""
    assert state.proposal.terminal_outcome is protocol.TerminalOutcome.CONVERGED


def test_stale_mutation_does_not_change_state(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    next_state = round_prep(root=tmp_path, expected_fingerprint=state.fingerprint, round_number=1)
    assert next_state.fingerprint != state.fingerprint
