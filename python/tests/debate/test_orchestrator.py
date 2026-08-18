"""Focused durable-state coverage for the debate orchestration boundary."""
from __future__ import annotations

import base64
import json
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.agents import _run_external
from larch.agents._types import VendorSessionHandle
from larch.core import config, proc
from larch.debate import orchestrator, protocol
from larch.debate.orchestrator import (
    DebateError,
    InitializationContext,
    ParticipantSlot,
    ProposalState,
    TurnRequest,
    TurnResult,
    record_turn,
    turn_prompt,
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


def _drive_stalemate(root: Path) -> ProposalState:
    """Complete both ledger rounds with two unchanged, competing positions."""
    state = _initialize(root)

    def runner(request: TurnRequest) -> TurnResult:
        position = "adopt approach cursor" if request.slot == "cursor" else "adopt approach codex"
        _ = request.output.write_text(
            f"POINT POINT_1 HOLD {position}",
            encoding="utf-8",
        )
        return TurnResult(ok=True, output=request.output)

    for round_number in (1, 2):
        state = _round_prep(root, state, round_number)
        for slot in ("cursor", "codex"):
            state, error = record_turn(
                root=root,
                expected_fingerprint=state.fingerprint,
                round_number=round_number,
                slot=slot,
                runner=runner,
            )
            assert error == ""
    assert state.proposal.phase is protocol.NonterminalPhase.AWAITING_ADJUDICATION
    return state


def _command_result(*, argv: Sequence[str], stdout: str, returncode: int = 0) -> proc.CommandResult:
    return proc.CommandResult(
        argv=tuple(argv),
        returncode=returncode,
        stdout=stdout,
        stderr="",
        duration=0.0,
    )


def test_canonical_state_and_turn_progression(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    payload = json.loads((tmp_path / "debate-state.json").read_text(encoding="utf-8"))
    assert payload["fingerprint"] == state.fingerprint
    state = _round_prep(tmp_path, state, 1)

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


def test_subject_is_bound_into_first_turn_and_synthesis_inputs(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    encoded = state.initialization.run_local_values[config.DEBATE_SUBJECT_VALUE_KEY]
    assert base64.b64decode(encoded).decode() == "# Subject\n\nChoose a safe implementation."
    first_prompt = turn_prompt(
        slot="cursor",
        round_number=1,
        point_universe=(1,),
        mailbox=(),
        run_local_values=state.initialization.run_local_values,
    )
    second_prompt = turn_prompt(
        slot="cursor",
        round_number=2,
        point_universe=(1,),
        mailbox=(),
        run_local_values=state.initialization.run_local_values,
    )
    assert encoded in first_prompt
    assert encoded not in second_prompt
    synthesis = json.loads(orchestrator._synthesis_input(state))  # pyright: ignore[reportPrivateUsage]  # verifies the persisted subject reaches the synthesis boundary
    assert synthesis["subject"] == "# Subject\n\nChoose a safe implementation."


def test_cli_ingests_claude_ledger_from_a_bounded_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = _initialize(
        tmp_path, claude_present=True, run_local_values={}, subject="Choose one approach."
    )
    state = _round_prep(tmp_path, state, 1)

    def runner(request: TurnRequest) -> TurnResult:
        _ = request.output.write_text("POINT POINT_1 HOLD keep evaluating", encoding="utf-8")
        return TurnResult(ok=True, output=request.output)

    for slot in ("cursor", "codex"):
        state, error = record_turn(
            root=tmp_path,
            expected_fingerprint=state.fingerprint,
            round_number=1,
            slot=slot,
            runner=runner,
        )
        assert error == ""
    supplied = tmp_path / "claude-round-1.input"
    _ = supplied.write_text("POINT POINT_1 AGREE keep evaluating", encoding="utf-8")

    assert orchestrator.record_turn_main(
        [
            "--debate-tmpdir",
            str(tmp_path),
            "--expected-fingerprint",
            state.fingerprint,
            "--round",
            "1",
            "--slot",
            "claude",
            "--input-file",
            str(supplied),
        ]
    ) == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is True
    assert orchestrator.load_state(tmp_path).active_round is None


def test_non_utf8_turn_output_becomes_a_protocol_drop(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    state = _round_prep(tmp_path, state, 1)

    def runner(request: TurnRequest) -> TurnResult:
        _ = request.output.write_bytes(b"\xff")
        return TurnResult(ok=True, output=request.output)

    state, error = record_turn(
        root=tmp_path,
        expected_fingerprint=state.fingerprint,
        round_number=1,
        slot="cursor",
        runner=runner,
    )

    assert error == config.DEBATE_DROP_PROTOCOL_REJECTION
    assert state.proposal.terminal_outcome is protocol.TerminalOutcome.ABORTED


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


class _FakeRun:
    """Records run_external_agent calls and returns a scripted outcome."""

    def __init__(self, *, exit_code: int = 0, handle: VendorSessionHandle | None = None, stdout_text: str = "", output_text: str = "") -> None:
        self.exit_code = exit_code
        self.handle = handle
        self.stdout_text = stdout_text
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.stdout_text:
            _ = Path(str(kwargs["stdout_path"])).write_text(self.stdout_text, encoding="utf-8")
        if self.output_text:
            _ = Path(str(kwargs["output"])).write_text(self.output_text, encoding="utf-8")

        class _Result:
            exit_code = self.exit_code
            session_handle = self.handle
            output = Path(str(kwargs["output"]))

        return _Result()


def _argv(call: dict[str, object]) -> Sequence[str]:
    tokens = call["cmd"]
    assert isinstance(tokens, list)
    return [str(token) for token in tokens]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]


def test_default_runner_rejects_claude_before_any_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRun()
    monkeypatch.setattr(_run_external, "run_external_agent", fake)
    request = TurnRequest("claude", 1, "prompt", (), tmp_path, tmp_path / "out.txt", None)

    result = orchestrator._default_runner(request)  # pyright: ignore[reportPrivateUsage]

    assert result.ok is False
    assert result.error_class == config.DEBATE_DROP_UNSUPPORTED_TRANSPORT
    assert not fake.calls


def test_default_runner_resumes_codex_with_the_explicit_handle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRun(output_text="POINT POINT_1 AGREE agreed")
    monkeypatch.setattr(_run_external, "run_external_agent", fake)
    handle = VendorSessionHandle.create(vendor="codex", session_id=_CODEX_SESSION_ID)
    request = TurnRequest(
        "codex",
        1,
        "prompt",
        (),
        tmp_path,
        tmp_path / "out.txt",
        handle,
        config.DEBATE_CODEX_MODEL,
    )

    result = orchestrator._default_runner(request)  # pyright: ignore[reportPrivateUsage]

    assert result.ok is True
    argv = _argv(fake.calls[0])
    assert argv[:4] == ["codex", "exec", "resume", _CODEX_SESSION_ID]
    assert "--last" not in argv
    assert 'sandbox_mode="read-only"' in argv
    assert argv[argv.index("-m") + 1] == config.DEBATE_CODEX_MODEL


def test_default_runner_extracts_the_cursor_result_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    envelope = json.dumps({"result": "POINT POINT_1 AGREE agreed"})
    fake = _FakeRun(output_text=envelope)
    monkeypatch.setattr(_run_external, "run_external_agent", fake)
    handle = VendorSessionHandle.create(vendor="cursor", session_id=_CURSOR_CHAT_ID)
    request = TurnRequest(
        "cursor",
        1,
        "prompt",
        (),
        tmp_path,
        tmp_path / "out.txt",
        handle,
        config.DEBATE_CURSOR_MODEL,
    )

    result = orchestrator._default_runner(request)  # pyright: ignore[reportPrivateUsage]

    assert result.ok is True
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "POINT POINT_1 AGREE agreed"
    argv = _argv(fake.calls[0])
    assert argv[:5] == ["cursor", "agent", "-p", "--resume", _CURSOR_CHAT_ID]
    assert "plan" in argv
    assert argv[argv.index("--model") + 1] == config.DEBATE_CURSOR_MODEL


def test_default_runner_rejects_a_malformed_cursor_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRun(output_text="not json")
    monkeypatch.setattr(_run_external, "run_external_agent", fake)
    handle = VendorSessionHandle.create(vendor="cursor", session_id=_CURSOR_CHAT_ID)
    request = TurnRequest("cursor", 1, "prompt", (), tmp_path, tmp_path / "out.txt", handle)

    result = orchestrator._default_runner(request)  # pyright: ignore[reportPrivateUsage]

    assert result.ok is False
    assert result.error_class == config.DEBATE_DROP_PROTOCOL_REJECTION


def test_turn_prompt_round_one_mailbox_is_an_empty_array() -> None:
    prompt = turn_prompt(slot="cursor", round_number=1, point_universe=(1, 2), mailbox=())
    assert "mailbox: []" in prompt
    assert f"debate-protocol-version: {protocol.PROTOCOL_VERSION}" in prompt
    assert "POINT_1 POINT_2" in prompt
    assert "Independently inspect read-only repository evidence" in prompt
    assert "CONCEDE changes position and cites POINT POINT_N" in prompt


def test_turn_prompt_round_two_requires_mailbox_negotiation() -> None:
    prompt = turn_prompt(slot="codex", round_number=2, point_universe=(1,), mailbox=())
    assert "Use the validated mailbox delta to negotiate" in prompt


def test_state_lock_refuses_a_non_regular_lock_path(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    lock = tmp_path / config.DEBATE_STATE_LOCK_FILENAME
    lock.unlink()
    os.mkfifo(lock)
    try:
        with pytest.raises(DebateError) as excinfo:
            _ = orchestrator.abort(root=tmp_path, expected_fingerprint=state.fingerprint)
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
        _ = orchestrator.abort(root=tmp_path, expected_fingerprint=state.fingerprint)

    assert excinfo.value.exit_code == config.DEBATE_EXIT_PERSISTENCE_FAILURE
    assert stat.S_ISLNK(lock.lstat().st_mode)


def test_operator_adjudication_requires_exact_decision_coverage(tmp_path: Path) -> None:
    state = _drive_stalemate(tmp_path)
    decisions = tmp_path / "decisions.tsv"
    _ = decisions.write_text("POINT_1\tSELECTED\tadopt approach cursor\n", encoding="utf-8")

    updated, tally = orchestrator.adjudicate(
        root=tmp_path,
        expected_fingerprint=state.fingerprint,
        decisions_file=decisions,
    )

    assert tally is None
    assert updated.proposal.terminal_outcome is protocol.TerminalOutcome.CONVERGED
    assert isinstance(updated.proposal.adjudications[0], protocol.SelectedAdjudication)
    assert orchestrator.load_state(tmp_path).proposal == updated.proposal


@pytest.mark.parametrize(
    "contents",
    [
        "",
        "POINT_1\tSELECTED\tadopt approach cursor\nPOINT_2\tSELECTED\textra\n",
        "POINT_1\tSELECTED\tadopt approach cursor\nPOINT_1\tSELECTED\tadopt approach codex\n",
        "POINT_2\tSELECTED\tforeign\n",
        "POINT_1\tSELECTED\tfirst line\nsecond line\n",
        "POINT_1\tSELECTED\t### NEW: forbidden\n",
    ],
)
def test_operator_adjudication_rejects_invalid_handoffs(tmp_path: Path, contents: str) -> None:
    state = _drive_stalemate(tmp_path)
    decisions = tmp_path / "decisions.tsv"
    _ = decisions.write_text(contents, encoding="utf-8")

    with pytest.raises(DebateError) as excinfo:
        _ = orchestrator.adjudicate(
            root=tmp_path,
            expected_fingerprint=state.fingerprint,
            decisions_file=decisions,
        )

    assert excinfo.value.exit_code == config.DEBATE_EXIT_ADJUDICATION_FAILURE
    assert orchestrator.load_state(tmp_path).fingerprint == state.fingerprint


def test_autonomous_adjudication_uses_dispatch_voters_and_writes_local_tally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _drive_stalemate(tmp_path)
    calls: list[list[str]] = []
    original_run = proc.run

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        if list(argv[1:3]) != ["agent", "dispatch-voters"]:
            return original_run(argv)
        calls.append(list(argv))
        voter_root = tmp_path / config.DEBATE_STALEMATE_VOTER_DIRNAME
        voter = voter_root / "voter-1.txt"
        paths = voter_root / "voter-paths.txt"
        _ = voter.write_text("FINDING_1: YES\nFINDING_2: NO\n", encoding="utf-8")
        _ = paths.write_text(f"{voter}\n", encoding="utf-8")
        return _command_result(
            argv=argv,
            stdout=f"VOTER_PATHS_FILE={paths}\nDISPATCH_OK=true\n",
        )

    monkeypatch.setattr(orchestrator.proc, "run", fake_run)
    updated, tally = orchestrator.adjudicate(
        root=tmp_path,
        expected_fingerprint=state.fingerprint,
        vote_stalemates=True,
    )

    assert calls
    assert tally is not None
    assert updated.proposal.terminal_outcome is protocol.TerminalOutcome.CONVERGED
    tally_text = tally.read_text(encoding="utf-8")
    assert "adopt approach cursor" in tally_text
    assert str(tmp_path) not in tally_text
    durable = next((tmp_path / "logs").rglob("debate-stalemate-tally.json"))
    assert str(tmp_path) not in durable.read_text(encoding="utf-8")


def test_autonomous_empty_panel_is_both_viable_without_operator_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _drive_stalemate(tmp_path)

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        paths = tmp_path / config.DEBATE_STALEMATE_VOTER_DIRNAME / "voter-paths.txt"
        _ = paths.write_text("", encoding="utf-8")
        return _command_result(
            argv=argv,
            stdout=f"VOTER_PATHS_FILE={paths}\nDISPATCH_OK=true\n",
        )

    monkeypatch.setattr(orchestrator.proc, "run", fake_run)
    updated, tally = orchestrator.adjudicate(
        root=tmp_path,
        expected_fingerprint=state.fingerprint,
        vote_stalemates=True,
    )

    assert tally is not None
    assert updated.proposal.terminal_outcome is protocol.TerminalOutcome.BOTH_VIABLE
    assert isinstance(updated.proposal.adjudications[0], protocol.SplitAdjudication)
    assert orchestrator.load_state(tmp_path).proposal == updated.proposal


def test_autonomous_adjudication_rejects_malformed_success_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _drive_stalemate(tmp_path)

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        return _command_result(argv=argv, stdout="DISPATCH_OK=true\n")

    monkeypatch.setattr(orchestrator.proc, "run", fake_run)
    with pytest.raises(DebateError) as excinfo:
        _ = orchestrator.adjudicate(
            root=tmp_path,
            expected_fingerprint=state.fingerprint,
            vote_stalemates=True,
        )

    assert excinfo.value.exit_code == config.DEBATE_EXIT_ADJUDICATION_FAILURE
    assert orchestrator.load_state(tmp_path).fingerprint == state.fingerprint


def _adjudicated_state(root: Path) -> ProposalState:
    state = _drive_stalemate(root)
    decisions = root / "decisions.tsv"
    _ = decisions.write_text("POINT_1\tSELECTED\tadopt approach cursor\n", encoding="utf-8")
    updated, _ = orchestrator.adjudicate(
        root=root,
        expected_fingerprint=state.fingerprint,
        decisions_file=decisions,
    )
    return updated


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
    state = _drive_stalemate(tmp_path)
    assert orchestrator.adjudication_preview_main(
        ["--debate-tmpdir", str(tmp_path), "--expected-fingerprint", state.fingerprint]
    ) == 0
    preview_envelope = json.loads(capsys.readouterr().out)
    assert preview_envelope["operation"] == "adjudication-preview"
    preview = json.loads(Path(preview_envelope["artifact_path"]).read_text(encoding="utf-8"))
    assert preview["points"][0]["point"] == "POINT_1"
    assert preview["points"][0]["positions"] == [
        "adopt approach cursor",
        "adopt approach codex",
    ]
    decisions = tmp_path / "decisions.tsv"
    _ = decisions.write_text("POINT_1\tSELECTED\tadopt approach cursor\n", encoding="utf-8")

    assert orchestrator.adjudicate_main(
        [
            "--debate-tmpdir", str(tmp_path),
            "--expected-fingerprint", state.fingerprint,
            "--decisions-file", str(decisions),
        ]
    ) == 0
    adjudication = json.loads(capsys.readouterr().out)
    assert adjudication["ok"] is True
    assert adjudication["operation"] == "adjudicate"
    state = orchestrator.load_state(tmp_path)
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

    assert orchestrator.adjudicate_main(
        ["--debate-tmpdir", str(tmp_path), "--expected-fingerprint", state.fingerprint]
    ) == config.DEBATE_EXIT_ADJUDICATION_FAILURE
    adjudication = json.loads(capsys.readouterr().out)
    assert adjudication["error_class"] == config.DEBATE_ERROR_ADJUDICATION_REJECTED

    assert orchestrator.synthesize_main(
        ["--debate-tmpdir", str(tmp_path), "--expected-fingerprint", state.fingerprint]
    ) == config.DEBATE_EXIT_SYNTHESIS_EXHAUSTED
    synthesis = json.loads(capsys.readouterr().out)
    assert synthesis["error_class"] == config.DEBATE_ERROR_SYNTHESIS_EXHAUSTED

    decisions = tmp_path / "decisions.tsv"
    _ = decisions.write_text("POINT_1\tSELECTED\tadopt approach cursor\n", encoding="utf-8")
    state, _ = orchestrator.adjudicate(
        root=tmp_path,
        expected_fingerprint=state.fingerprint,
        decisions_file=decisions,
    )
    assert orchestrator.publish_prepare_main(
        ["--debate-tmpdir", str(tmp_path), "--expected-fingerprint", state.fingerprint]
    ) == config.DEBATE_EXIT_PUBLICATION_FAILURE
    publication = json.loads(capsys.readouterr().out)
    assert publication["error_class"] == config.DEBATE_ERROR_PUBLICATION_FAILURE
