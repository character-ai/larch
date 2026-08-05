"""Focused durable-state coverage for the debate orchestration boundary."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.agents import _run_external
from larch.agents._types import VendorSessionHandle
from larch.core import config
from larch.debate import orchestrator, protocol
from larch.debate.orchestrator import (
    DebateError,
    InitializationContext,
    ParticipantSlot,
    ProposalState,
    TurnRequest,
    TurnResult,
    default_bootstrapper,
    initialize,
    record_turn,
    round_prep,
    turn_prompt,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

_CURSOR_CHAT_ID = "chat-0123456789abcdef"
_CODEX_SESSION_ID = "6f1b2c3d-4e5f-4a6b-8c9d-0e1f2a3b4c5d"


def _fake_bootstrapper(slot: ParticipantSlot, context: InitializationContext) -> VendorSessionHandle:
    _ = context
    session_id = _CURSOR_CHAT_ID if slot.tool == "cursor" else _CODEX_SESSION_ID
    return VendorSessionHandle.create(vendor=slot.tool, session_id=session_id)


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
        bootstrapper=_fake_bootstrapper,
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


def test_initialize_persists_explicit_vendor_handles(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    handles = state.initialization.session_handles
    assert set(handles) == {"cursor", "codex"}
    assert handles["cursor"].session_id == _CURSOR_CHAT_ID
    assert handles["codex"].session_id == _CODEX_SESSION_ID
    # Handles survive the canonical round trip, so a later turn can resume them.
    payload = json.loads((tmp_path / "debate-state.json").read_text(encoding="utf-8"))
    assert payload["initialization"]["session_handles"]["codex"]["session_id"] == _CODEX_SESSION_ID


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


def test_default_bootstrapper_creates_cursor_session_from_structured_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    handle = VendorSessionHandle.create(vendor="cursor", session_id=_CURSOR_CHAT_ID)
    fake = _FakeRun(handle=handle, stdout_text=json.dumps({"chatId": _CURSOR_CHAT_ID}) + "\n")
    monkeypatch.setattr(_run_external, "run_external_agent", fake)
    logs = tmp_path / "logs"
    logs.mkdir()
    context = InitializationContext((1,), {}, str(tmp_path), str(logs), "run", (), orchestrator.RestoreMetadata("1", "a", "b"))
    slot = ParticipantSlot("cursor", "cursor", "subprocess", available=True)

    created = default_bootstrapper(slot, context)

    assert created.session_id == _CURSOR_CHAT_ID
    assert _argv(fake.calls[0]) == ["cursor", "agent", "create-chat"]
    assert fake.calls[0]["capture_session_handle"] is True


def test_default_bootstrapper_fails_closed_without_a_handle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_run_external, "run_external_agent", _FakeRun(handle=None))
    logs = tmp_path / "logs"
    logs.mkdir()
    context = InitializationContext((1,), {}, str(tmp_path), str(logs), "run", (), orchestrator.RestoreMetadata("1", "a", "b"))

    with pytest.raises(DebateError) as excinfo:
        _ = default_bootstrapper(ParticipantSlot("codex", "codex", "subprocess", available=True), context)

    assert excinfo.value.exit_code == config.DEBATE_EXIT_RUNNER_FAILURE


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
    request = TurnRequest("codex", 1, "prompt", (), tmp_path, tmp_path / "out.txt", handle)

    result = orchestrator._default_runner(request)  # pyright: ignore[reportPrivateUsage]

    assert result.ok is True
    argv = _argv(fake.calls[0])
    assert argv[:4] == ["codex", "exec", "resume", _CODEX_SESSION_ID]
    assert "--last" not in argv
    assert 'sandbox_mode="read-only"' in argv


def test_default_runner_extracts_the_cursor_result_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    envelope = json.dumps({"result": "POINT POINT_1 AGREE agreed"})
    fake = _FakeRun(output_text=envelope)
    monkeypatch.setattr(_run_external, "run_external_agent", fake)
    handle = VendorSessionHandle.create(vendor="cursor", session_id=_CURSOR_CHAT_ID)
    request = TurnRequest("cursor", 1, "prompt", (), tmp_path, tmp_path / "out.txt", handle)

    result = orchestrator._default_runner(request)  # pyright: ignore[reportPrivateUsage]

    assert result.ok is True
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "POINT POINT_1 AGREE agreed"
    argv = _argv(fake.calls[0])
    assert argv[:5] == ["cursor", "agent", "-p", "--resume", _CURSOR_CHAT_ID]
    assert "plan" in argv


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


def test_state_lock_refuses_a_non_regular_lock_path(tmp_path: Path) -> None:
    state = _initialize(tmp_path)
    lock = tmp_path / config.DEBATE_STATE_LOCK_FILENAME
    lock.unlink()
    os.mkfifo(lock)
    try:
        with pytest.raises(DebateError) as excinfo:
            _ = round_prep(root=tmp_path, expected_fingerprint=state.fingerprint, round_number=1)
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
        _ = round_prep(root=tmp_path, expected_fingerprint=state.fingerprint, round_number=1)

    assert excinfo.value.exit_code == config.DEBATE_EXIT_PERSISTENCE_FAILURE
    assert stat.S_ISLNK(lock.lstat().st_mode)
