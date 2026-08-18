"""Focused durable-state coverage for the debate orchestration boundary."""
from __future__ import annotations

import base64
import json
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.agents._types import VendorSessionHandle
from larch.core import config, proc
from larch.debate import orchestrator, protocol
from larch.debate.orchestrator import (
    DebateError,
    InitializationContext,
    ParticipantSlot,
    ProposalState,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

_CURSOR_CHAT_ID = "chat-0123456789abcdef"
_CODEX_SESSION_ID = "6f1b2c3d-4e5f-4a6b-8c9d-0e1f2a3b4c5d"


def _initialize(
    root: Path,
    *,
    cursor_present: bool = True,
    codex_present: bool = True,
    claude_present: bool = False,
    run_local_values: dict[str, str] | None = None,
    subject: str = "# Subject\n\nChoose a safe implementation.",
) -> ProposalState:
    """Build an initial debate state directly.

    ``debate init`` and ``debate round-prep`` are Rust-owned after #8600, so
    these tests exercise the still-Python commands (record-turn, adjudicate,
    synthesize, publish-prepare, abort) against a state assembled here rather
    than through the removed Python builders.
    """
    (root / "logs").mkdir(exist_ok=True)
    base = {"run": "local"} if run_local_values is None else run_local_values
    values = dict(sorted(base.items()))
    values[config.DEBATE_SUBJECT_VALUE_KEY] = base64.b64encode(subject.encode("utf-8")).decode("ascii")
    values = dict(sorted(values.items()))
    availability = {"cursor": cursor_present, "codex": codex_present, "claude": claude_present}
    seats = (
        ("cursor", "cursor", "subprocess", config.DEBATE_CURSOR_MODEL),
        ("codex", "codex", "subprocess", config.DEBATE_CODEX_MODEL),
        ("claude", "claude", "agent-tool", config.DEBATE_CLAUDE_MODEL),
    )
    slots = tuple(
        ParticipantSlot(slot, tool, transport, availability[tool], model)
        for slot, tool, transport, model in seats
    )
    handles: dict[str, VendorSessionHandle] = {}
    for slot in slots:
        if slot.available and slot.transport == "subprocess":
            session_id = _CURSOR_CHAT_ID if slot.tool == "cursor" else _CODEX_SESSION_ID
            handles[slot.slot] = VendorSessionHandle.create(vendor=slot.tool, session_id=session_id)
    restore = orchestrator.RestoreMetadata("1", "old", "new")
    context = InitializationContext(
        (1,), values, str(Path.cwd()), str(root / "logs"), "test-run", slots, restore, handles, ""
    )
    proposal = protocol.new_proposal((protocol.PointId(1),), run_local_values=values)
    state = orchestrator.write_state(root, ProposalState(context, proposal, None))
    # Materialize the per-debate lock file so lock-path tests can mutate it.
    with orchestrator._StateLock(orchestrator._trusted_root(root)):  # pyright: ignore[reportPrivateUsage]  # test scaffolding for the still-Python state lock
        pass
    return state


def _round_prep(root: Path, state: ProposalState, round_number: int) -> ProposalState:
    """Prepare one negotiation round directly (round-prep is Rust-owned)."""
    live = tuple(slot.slot for slot in state.initialization.slots if slot.available)
    previous = state.proposal.rounds[-1] if state.proposal.rounds else None
    mailboxes: dict[str, tuple[dict[str, object], ...]] = {}
    for slot in live:
        mailboxes[slot] = (
            ()
            if previous is None
            else tuple(
                orchestrator._encode_binding(binding)  # pyright: ignore[reportPrivateUsage]  # mailbox delta reuses the persisted binding encoder
                for binding in previous.bindings
                if binding.slot.value != slot
            )
        )
    active = orchestrator.ActiveRound(round_number, True, mailboxes, live, live)  # noqa: FBT003 - frozen active-round constructor mirrors the persisted positional schema
    return orchestrator.write_state(
        root, ProposalState(state.initialization, state.proposal, active, state.drops)
    )


def _submit_round(
    root: Path, state: ProposalState, round_number: int, positions: dict[str, str]
) -> ProposalState:
    """Submit one round directly through the protocol machine.

    ``record-turn`` is Rust-owned after #8601, so retained-verb tests assemble
    submitted rounds from parsed ledgers rather than through a Python runner.
    """
    live = tuple(slot.slot for slot in state.initialization.slots if slot.available)
    bindings: dict[str, protocol.SlotLedgerBinding] = {}
    for slot in live:
        ledger = protocol.parse_slot_ledger(f"POINT POINT_1 HOLD {positions[slot]}")
        fingerprints = tuple(
            protocol.fingerprint_reason(row.reason, run_local_values=state.proposal.run_local_values)
            for row in ledger.rows
        )
        bindings[slot] = protocol.SlotLedgerBinding(
            slot=protocol.parse_slot(slot),
            ledger=ledger,
            fingerprints=fingerprints,
            run_local_values=state.proposal.run_local_values,
        )
    ordered = tuple(bindings[slot] for slot in protocol.SLOT_ORDER if slot in bindings)
    proposal = protocol.transition(
        state.proposal,
        protocol.TransitionAction.SUBMIT_ROUND,
        round_state=protocol.RoundState(protocol.RoundNumber(round_number), ordered),
    )
    return orchestrator.write_state(
        root, ProposalState(state.initialization, proposal, None, state.drops)
    )


def _drive_stalemate(root: Path) -> ProposalState:
    """Complete both ledger rounds with two unchanged, competing positions."""
    state = _initialize(root)
    positions = {"cursor": "adopt approach cursor", "codex": "adopt approach codex"}
    for round_number in (1, 2):
        state = _submit_round(root, state, round_number, positions)
    assert state.proposal.phase is protocol.NonterminalPhase.AWAITING_ADJUDICATION
    return state


def _adjudicate(
    root: Path, state: ProposalState, records: Sequence[protocol.AdjudicationRecord]
) -> ProposalState:
    """Adjudicate directly through the protocol machine.

    ``adjudicate`` and ``adjudication-preview`` are Rust-owned after #8602, so
    retained synthesize/publish-prepare tests assemble an adjudicated proposal
    here rather than through the removed Python command.
    """
    proposal = protocol.transition(
        state.proposal,
        protocol.TransitionAction.ADJUDICATE,
        adjudications=tuple(records),
    )
    return orchestrator.write_state(
        root, ProposalState(state.initialization, proposal, state.active_round, state.drops)
    )


def _command_result(*, argv: Sequence[str], stdout: str, returncode: int = 0) -> proc.CommandResult:
    return proc.CommandResult(
        argv=tuple(argv),
        returncode=returncode,
        stdout=stdout,
        stderr="",
        duration=0.0,
    )


def test_subject_is_bound_into_synthesis_inputs(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    encoded = state.initialization.run_local_values[config.DEBATE_SUBJECT_VALUE_KEY]
    assert base64.b64decode(encoded).decode() == "# Subject\n\nChoose a safe implementation."
    synthesis = json.loads(orchestrator._synthesis_input(state))  # pyright: ignore[reportPrivateUsage]  # verifies the persisted subject reaches the synthesis boundary
    assert synthesis["subject"] == "# Subject\n\nChoose a safe implementation."


def test_stale_mutation_does_not_change_state(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    next_state = _round_prep(tmp_path, state, 1)
    assert next_state.fingerprint != state.fingerprint


def test_initialize_persists_explicit_vendor_handles(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    handles = state.initialization.session_handles
    assert set(handles) == {"cursor", "codex"}
    assert handles["cursor"].session_id == _CURSOR_CHAT_ID
    assert handles["codex"].session_id == _CODEX_SESSION_ID
    # Handles survive the canonical round trip, so a later turn can resume them.
    payload = json.loads((tmp_path / "debate-state.json").read_text(encoding="utf-8"))
    assert payload["initialization"]["session_handles"]["codex"]["session_id"] == _CODEX_SESSION_ID


def test_load_state_accepts_the_piece_one_schema(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    state_file = tmp_path / config.DEBATE_STATE_FILENAME
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    payload["schema_version"] = 1
    del payload["proposal"]["disputes"]
    del payload["proposal"]["adjudications"]
    payload["fingerprint"] = orchestrator._fingerprint_payload(payload)  # pyright: ignore[reportPrivateUsage]  # state compatibility needs the canonical payload hash
    _ = state_file.write_text(
        orchestrator._canonical_json(payload),  # pyright: ignore[reportPrivateUsage]  # state compatibility needs canonical wire encoding
        encoding="utf-8",
    )

    loaded = orchestrator.load_state(tmp_path)

    assert loaded.proposal == state.proposal


def test_state_lock_refuses_a_non_regular_lock_path(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    lock = tmp_path / config.DEBATE_STATE_LOCK_FILENAME
    lock.unlink()
    os.mkfifo(lock)
    try:
        with pytest.raises(DebateError) as excinfo:
            _ = orchestrator.publish_prepare(root=tmp_path, expected_fingerprint=state.fingerprint)
        assert excinfo.value.exit_code == config.DEBATE_EXIT_PERSISTENCE_FAILURE
    finally:
        lock.unlink()


def test_state_lock_refuses_a_symlinked_lock_path(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    lock = tmp_path / config.DEBATE_STATE_LOCK_FILENAME
    lock.unlink()
    target = tmp_path / "elsewhere.lock"
    _ = target.write_text("", encoding="utf-8")
    lock.symlink_to(target)

    with pytest.raises(DebateError) as excinfo:
        _ = orchestrator.publish_prepare(root=tmp_path, expected_fingerprint=state.fingerprint)

    assert excinfo.value.exit_code == config.DEBATE_EXIT_PERSISTENCE_FAILURE
    assert stat.S_ISLNK(lock.lstat().st_mode)


def _adjudicated_state(root: Path) -> ProposalState:
    state = _drive_stalemate(root)
    return _adjudicate(
        root,
        state,
        (protocol.SelectedAdjudication(protocol.PointId(1), "adopt approach cursor"),),
    )


def test_synthesize_redacts_and_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = _adjudicated_state(tmp_path)
    calls = 0
    original_run = proc.run

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        nonlocal calls
        if list(argv[1:3]) != ["agent", "dispatch-waterfall"]:
            return original_run(argv)
        calls += 1
        output = tmp_path / config.DEBATE_SYNTHESIS_OUTPUT_FILENAME
        paths = tmp_path / "synthesizer-paths.txt"
        _ = output.write_text("# Clear proposal\n\nUse the selected approach.\n", encoding="utf-8")
        _ = paths.write_text(f"{output}\n", encoding="utf-8")
        return _command_result(
            argv=argv,
            stdout=f"ALL_OUTPUT_FILES_PATH={paths}\nDISPATCH_OK=true\n",
        )

    monkeypatch.setattr(orchestrator.proc, "run", fake_run)
    returned, body = orchestrator.synthesize(root=tmp_path, expected_fingerprint=state.fingerprint)

    assert returned.fingerprint == state.fingerprint
    assert body.name == config.DEBATE_PROPOSAL_BODY_FILENAME
    assert (tmp_path / config.DEBATE_PROPOSAL_TITLE_FILENAME).read_text(encoding="utf-8") == "[PROPOSAL] Clear proposal\n"
    assert body.read_text(encoding="utf-8") == "Use the selected approach.\n"
    assert (tmp_path / config.DEBATE_SYNTHESIS_MARKER_FILENAME).is_file()
    assert calls == 1
    _, repeated = orchestrator.synthesize(root=tmp_path, expected_fingerprint=state.fingerprint)
    assert repeated == body
    assert calls == 1
    durable = next((tmp_path / "logs").rglob("debate-proposal.md"))
    assert str(tmp_path) not in durable.read_text(encoding="utf-8")


@pytest.mark.parametrize("forbidden", ["### NEW: a file\n", "diff_lines: 3\n"])
def test_synthesis_rejects_plan_grammar_and_remains_retriable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, forbidden: str
) -> None:
    state = _adjudicated_state(tmp_path)
    output = tmp_path / config.DEBATE_SYNTHESIS_OUTPUT_FILENAME
    paths = tmp_path / "synthesizer-paths.txt"
    attempts = 0
    original_run = proc.run

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        nonlocal attempts
        if list(argv[1:3]) != ["agent", "dispatch-waterfall"]:
            return original_run(argv)
        attempts += 1
        body = forbidden if attempts == 1 else "A valid body.\n"
        _ = output.write_text(f"# Proposal\n\n{body}", encoding="utf-8")
        _ = paths.write_text(f"{output}\n", encoding="utf-8")
        return _command_result(
            argv=argv,
            stdout=f"ALL_OUTPUT_FILES_PATH={paths}\nDISPATCH_OK=true\n",
        )

    monkeypatch.setattr(orchestrator.proc, "run", fake_run)
    with pytest.raises(DebateError) as excinfo:
        _ = orchestrator.synthesize(root=tmp_path, expected_fingerprint=state.fingerprint)
    assert excinfo.value.exit_code == config.DEBATE_EXIT_SYNTHESIS_EXHAUSTED
    assert not (tmp_path / config.DEBATE_SYNTHESIS_MARKER_FILENAME).exists()

    _, body = orchestrator.synthesize(root=tmp_path, expected_fingerprint=state.fingerprint)
    assert body.is_file()
    assert attempts == 2


@pytest.mark.parametrize("title", ["--force", "[PROPOSAL] --force", "[proposal] --force"])
def test_synthesis_rejects_an_option_shaped_proposal_title(title: str) -> None:
    with pytest.raises(DebateError, match="invalid title"):
        _ = orchestrator._proposal_parts(f"# {title}\n\nSafe body")  # pyright: ignore[reportPrivateUsage]  # /issue receives the title as a positional argument


def test_synthesis_normalizes_a_case_variant_proposal_prefix() -> None:
    title, body = orchestrator._proposal_parts("# [proposal] Safe queue\n\nUse bounds.")  # pyright: ignore[reportPrivateUsage]  # validates the canonical title passed to /issue
    assert (title, body) == ("Safe queue", "Use bounds.")


def test_synthesis_waterfall_exhaustion_is_retriable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _adjudicated_state(tmp_path)
    output = tmp_path / config.DEBATE_SYNTHESIS_OUTPUT_FILENAME
    paths = tmp_path / "synthesizer-paths.txt"
    attempts = 0
    original_run = proc.run

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        nonlocal attempts
        if list(argv[1:3]) != ["agent", "dispatch-waterfall"]:
            return original_run(argv)
        attempts += 1
        if attempts == 1:
            return _command_result(argv=argv, stdout="DISPATCH_OK=false\n", returncode=1)
        _ = output.write_text("# Proposal\n\nProposal body.\n", encoding="utf-8")
        _ = paths.write_text(f"{output}\n", encoding="utf-8")
        return _command_result(
            argv=argv,
            stdout=f"ALL_OUTPUT_FILES_PATH={paths}\nDISPATCH_OK=true\n",
        )

    monkeypatch.setattr(orchestrator.proc, "run", fake_run)
    with pytest.raises(DebateError) as excinfo:
        _ = orchestrator.synthesize(root=tmp_path, expected_fingerprint=state.fingerprint)
    assert excinfo.value.exit_code == config.DEBATE_EXIT_SYNTHESIS_EXHAUSTED
    assert not (tmp_path / config.DEBATE_SYNTHESIS_MARKER_FILENAME).exists()

    _, body = orchestrator.synthesize(root=tmp_path, expected_fingerprint=state.fingerprint)
    assert body.is_file()
    assert attempts == 2


def test_publish_prepare_is_local_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _adjudicated_state(tmp_path)
    original_run = proc.run

    def synthesize_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        if list(argv[1:3]) != ["agent", "dispatch-waterfall"]:
            return original_run(argv)
        output = tmp_path / config.DEBATE_SYNTHESIS_OUTPUT_FILENAME
        paths = tmp_path / "synthesizer-paths.txt"
        _ = output.write_text("# Proposal\n\nProposal body.\n", encoding="utf-8")
        _ = paths.write_text(f"{output}\n", encoding="utf-8")
        return _command_result(
            argv=argv,
            stdout=f"ALL_OUTPUT_FILES_PATH={paths}\nDISPATCH_OK=true\n",
        )

    monkeypatch.setattr(orchestrator.proc, "run", synthesize_run)
    state, _ = orchestrator.synthesize(root=tmp_path, expected_fingerprint=state.fingerprint)

    def no_process(*_args: object, **_kwargs: object) -> proc.CommandResult:
        raise AssertionError("publish preparation must not launch a process")

    monkeypatch.setattr(orchestrator.proc, "run", no_process)
    returned, handoff = orchestrator.publish_prepare(
        root=tmp_path,
        expected_fingerprint=state.fingerprint,
    )
    again, repeated = orchestrator.publish_prepare(
        root=tmp_path,
        expected_fingerprint=state.fingerprint,
    )

    assert returned == again == state
    assert handoff == repeated
    values = handoff.read_text(encoding="utf-8")
    assert "TITLE_FILE=" in values
    assert "BODY_FILE=" in values
    assert "SOURCE_ISSUE_NUMBER=1" in values
    assert "CROSS_LINK_ISSUE_NUMBER=1" in values


def test_new_debate_verbs_emit_machine_envelopes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    state = _adjudicated_state(tmp_path)
    original_run = proc.run

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        if list(argv[1:3]) != ["agent", "dispatch-waterfall"]:
            return original_run(argv)
        output = tmp_path / config.DEBATE_SYNTHESIS_OUTPUT_FILENAME
        paths = tmp_path / "synthesizer-paths.txt"
        _ = output.write_text("# Proposal\n\nProposal body.\n", encoding="utf-8")
        _ = paths.write_text(f"{output}\n", encoding="utf-8")
        return _command_result(
            argv=argv,
            stdout=f"ALL_OUTPUT_FILES_PATH={paths}\nDISPATCH_OK=true\n",
        )

    monkeypatch.setattr(orchestrator.proc, "run", fake_run)
    assert orchestrator.synthesize_main(
        ["--debate-tmpdir", str(tmp_path), "--expected-fingerprint", state.fingerprint]
    ) == 0
    synthesis = json.loads(capsys.readouterr().out)
    assert synthesis["ok"] is True
    assert synthesis["operation"] == "synthesize"
    assert orchestrator.publish_prepare_main(
        ["--debate-tmpdir", str(tmp_path), "--expected-fingerprint", state.fingerprint]
    ) == 0
    publication = json.loads(capsys.readouterr().out)
    assert publication["ok"] is True
    assert publication["operation"] == "publish-prepare"


def test_new_debate_verbs_emit_distinct_failure_classes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = _drive_stalemate(tmp_path)

    assert orchestrator.synthesize_main(
        ["--debate-tmpdir", str(tmp_path), "--expected-fingerprint", state.fingerprint]
    ) == config.DEBATE_EXIT_SYNTHESIS_EXHAUSTED
    synthesis = json.loads(capsys.readouterr().out)
    assert synthesis["error_class"] == config.DEBATE_ERROR_SYNTHESIS_EXHAUSTED

    state = _adjudicate(
        tmp_path,
        state,
        (protocol.SelectedAdjudication(protocol.PointId(1), "adopt approach cursor"),),
    )
    assert orchestrator.publish_prepare_main(
        ["--debate-tmpdir", str(tmp_path), "--expected-fingerprint", state.fingerprint]
    ) == config.DEBATE_EXIT_PUBLICATION_FAILURE
    publication = json.loads(capsys.readouterr().out)
    assert publication["error_class"] == config.DEBATE_ERROR_PUBLICATION_FAILURE
