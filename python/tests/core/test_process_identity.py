# pyright: reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownParameterType=false
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from larch.core import process_identity
from larch.core.proc import CommandResult


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:
        key = tuple(argv)
        self.calls.append(key)
        return self.responses.get(key, CommandResult(key, 1, "", "", 0.01))


def _ps(pid: int, command: str = "/usr/bin/python3 /repo/python/cli.py plan-review run") -> CommandResult:
    return CommandResult(
        ("ps", "-p", str(pid), "-o", "lstart=", "-o", "command="),
        0,
        f"Fri Jul  3 17:01:02 2026 {command}\n",
        "",
        0.01,
    )


def test_captures_ps_start_time_and_command(monkeypatch) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    runner = FakeRunner({("ps", "-p", "123", "-o", "lstart=", "-o", "command="): _ps(123)})

    identity = process_identity.read_process_identity(pid=123, runner=runner, expected_signature="plan-review run")

    assert identity == process_identity.RecordedProcessIdentity(
        pid=123,
        pgid=123,
        start_time="Fri Jul 3 17:01:02 2026",
        command_signature="/usr/bin/python3 /repo/python/cli.py plan-review run",
        expected_signature="plan-review run",
    )


def test_rejects_missing_pid(monkeypatch) -> None:
    def missing(_pid: int) -> int:
        raise ProcessLookupError

    monkeypatch.setattr(process_identity.os, "getpgid", missing)
    recorded = process_identity.RecordedProcessIdentity(123, 123, "x", "cmd", "cmd")

    assert process_identity.validate_process_identity(recorded=recorded).reason == "missing-pid"


def test_rejects_start_time_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    runner = FakeRunner({("ps", "-p", "123", "-o", "lstart=", "-o", "command="): _ps(123)})
    recorded = process_identity.RecordedProcessIdentity(123, 123, "Fri Jul 3 17:01:01 2026", "/usr/bin/python3 /repo/python/cli.py plan-review run", "plan-review run")

    assert process_identity.validate_process_identity(recorded=recorded, runner=runner).reason == "start-time-mismatch"


def test_rejects_command_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    runner = FakeRunner({("ps", "-p", "123", "-o", "lstart=", "-o", "command="): _ps(123, "sleep 100")})
    recorded = process_identity.RecordedProcessIdentity(123, 123, "Fri Jul 3 17:01:02 2026", "other command", "other")

    assert process_identity.validate_process_identity(recorded=recorded, runner=runner).reason == "command-mismatch"


def test_rejects_pgid_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda _pid: 456)
    runner = FakeRunner({("ps", "-p", "123", "-o", "lstart=", "-o", "command="): _ps(123)})
    recorded = process_identity.RecordedProcessIdentity(123, 123, "Fri Jul 3 17:01:02 2026", "/usr/bin/python3 /repo/python/cli.py plan-review run", "plan-review run")

    assert process_identity.validate_process_identity(recorded=recorded, runner=runner).reason == "pgid-mismatch"


def test_logs_before_kill(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    calls: list[str] = []
    monkeypatch.setattr(process_identity.os, "killpg", lambda _pgid, sig: calls.append(f"killpg:{sig}"))
    monkeypatch.setattr(process_identity.os, "kill", lambda _pid, sig: calls.append(f"kill:{sig}"))
    monkeypatch.setattr(process_identity.time, "sleep", lambda _seconds: None)
    runner = FakeRunner({
        ("ps", "-p", "123", "-o", "lstart=", "-o", "command="): _ps(123),
        ("pgrep", "-P", "123"): CommandResult(("pgrep", "-P", "123"), 1, "", "", 0.01),
    })
    recorded = process_identity.RecordedProcessIdentity(
        123,
        123,
        "Fri Jul 3 17:01:02 2026",
        "/usr/bin/python3 /repo/python/cli.py plan-review run",
        "plan-review run",
    )

    result = process_identity.terminate_validated_process_group(
        recorded=recorded,
        log_path=tmp_path / "kill.jsonl",
        caller="test",
        reason="unit",
        runner=runner,
    )

    assert result.ok
    first_log = json.loads((tmp_path / "kill.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert first_log["signal"] == "SIGTERM"
    assert calls


def test_does_not_sigkill_after_failed_validation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    signals: list[int] = []
    monkeypatch.setattr(process_identity.os, "killpg", lambda _pgid, sig: signals.append(sig))
    monkeypatch.setattr(process_identity.time, "sleep", lambda _seconds: None)
    good = _ps(123)
    bad = _ps(123, "recycled command")

    class ChangingRunner(FakeRunner):
        def run(self, argv: Sequence[str], **kwargs: object) -> CommandResult:
            if tuple(argv) == ("ps", "-p", "123", "-o", "lstart=", "-o", "command="):
                self.calls.append(tuple(argv))
                return good if len(self.calls) == 1 else bad
            return super().run(argv, **kwargs)

    runner = ChangingRunner({("pgrep", "-P", "123"): CommandResult(("pgrep", "-P", "123"), 1, "", "", 0.01)})
    recorded = process_identity.RecordedProcessIdentity(
        123,
        123,
        "Fri Jul 3 17:01:02 2026",
        "/usr/bin/python3 /repo/python/cli.py plan-review run",
        "plan-review run",
    )

    result = process_identity.terminate_validated_process_group(
        recorded=recorded,
        log_path=tmp_path / "kill.jsonl",
        caller="test",
        reason="unit",
        runner=runner,
    )

    assert result.reason == "command-mismatch"
    assert signals == [process_identity.signal.SIGTERM]
