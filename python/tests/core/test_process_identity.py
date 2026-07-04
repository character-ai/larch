# pyright: reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownParameterType=false
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from larch.core import config, process_identity
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


def test_append_kill_log_redacts_secret_fields(tmp_path: Path) -> None:
    secret = "sk-ant-abcdefghijklmnopqrstuvwx"
    log_path = tmp_path / "kill.jsonl"

    process_identity.append_kill_log(
        path=log_path,
        event=process_identity.KillLogEvent(
            event="signal",
            signal="SIGTERM",
            pid=123,
            pgid=123,
            command=f"python cli.py --token {secret}",
            caller=f"caller {secret}",
            reason=f"reason {secret}",
            descendants=(),
            tmpdir_needle=secret,
            physical_needle=secret,
        ),
    )

    text = log_path.read_text(encoding="utf-8")
    assert secret not in text
    assert config.REDACTED_TOKEN in text


def test_terminate_validated_process_group_revalidates_descendants_before_sigkill(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    kills: list[tuple[int, int]] = []
    monkeypatch.setattr(process_identity.os, "killpg", lambda _pgid, sig: kills.append((-1, sig)))
    monkeypatch.setattr(process_identity.os, "kill", lambda pid, sig: kills.append((pid, sig)))
    monkeypatch.setattr(process_identity.time, "sleep", lambda _seconds: None)
    good = _ps(123)
    first_descendants = CommandResult(("pgrep", "-P", "123"), 0, "10\n11\n", "", 0.01)
    second_descendants = CommandResult(("pgrep", "-P", "123"), 0, "11\n", "", 0.01)

    class ChangingRunner(FakeRunner):
        def run(self, argv: Sequence[str], **kwargs: object) -> CommandResult:
            key = tuple(argv)
            self.calls.append(key)
            if key == ("ps", "-p", "123", "-o", "lstart=", "-o", "command="):
                return good if self.calls.count(key) == 1 else good
            if key == ("pgrep", "-P", "123"):
                return first_descendants if self.calls.count(key) == 1 else second_descendants
            return super().run(argv, **kwargs)

    runner = ChangingRunner({
        ("pgrep", "-P", "10"): CommandResult(("pgrep", "-P", "10"), 1, "", "", 0.01),
        ("pgrep", "-P", "11"): CommandResult(("pgrep", "-P", "11"), 1, "", "", 0.01),
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
    assert kills == [
        (-1, process_identity.signal.SIGTERM),
        (10, process_identity.signal.SIGTERM),
        (11, process_identity.signal.SIGTERM),
        (-1, process_identity.signal.SIGKILL),
        (11, process_identity.signal.SIGKILL),
    ]


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


def test_terminate_validated_process_group_cleans_live_members_when_leader_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    kills: list[tuple[int, int]] = []
    monkeypatch.setattr(process_identity.os, "killpg", lambda _pgid, sig: kills.append((-1, sig)))
    monkeypatch.setattr(process_identity.os, "kill", lambda pid, sig: kills.append((pid, sig)))
    monkeypatch.setattr(process_identity.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(process_identity, "read_process_identity", lambda **_kwargs: None)
    member_calls = [(10, 11), (11,)]

    def fake_collect_process_group_members(*, pgid: int, **_kwargs: object) -> tuple[int, ...]:
        _ = pgid
        return member_calls.pop(0)

    monkeypatch.setattr(process_identity, "collect_process_group_members", fake_collect_process_group_members)

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
    )

    assert not result.ok
    assert result.reason == "missing-pid"
    assert kills == []


def test_terminate_validated_process_group_cleans_live_members_when_leader_missing_and_members_validate(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    kills: list[tuple[int, int]] = []
    monkeypatch.setattr(process_identity.os, "killpg", lambda _pgid, sig: kills.append((-1, sig)))
    monkeypatch.setattr(process_identity.os, "kill", lambda pid, sig: kills.append((pid, sig)))
    monkeypatch.setattr(process_identity.time, "sleep", lambda _seconds: None)
    identity = process_identity.RecordedProcessIdentity(
        123,
        123,
        "Fri Jul 3 17:01:02 2026",
        "/usr/bin/python3 /repo/python/cli.py plan-review run",
        "plan-review run",
    )

    def fake_read_process_identity(**_kwargs: object) -> process_identity.RecordedProcessIdentity | None:
        pid = int(_kwargs["pid"])
        if pid == 123:
            return None
        if pid in {10, 11}:
            return identity
        return None

    monkeypatch.setattr(process_identity, "read_process_identity", fake_read_process_identity)
    monkeypatch.setattr(process_identity, "collect_process_group_members", lambda **_kwargs: (10, 11))

    result = process_identity.terminate_validated_process_group(
        recorded=identity,
        log_path=tmp_path / "kill.jsonl",
        caller="test",
        reason="unit",
    )

    assert result.ok
    assert kills == [
        (-1, process_identity.signal.SIGTERM),
        (10, process_identity.signal.SIGTERM),
        (11, process_identity.signal.SIGTERM),
        (-1, process_identity.signal.SIGKILL),
        (10, process_identity.signal.SIGKILL),
        (11, process_identity.signal.SIGKILL),
    ]


def test_terminate_validated_process_group_escalates_live_members_when_leader_exits_before_sigkill(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(process_identity.os, "getpgid", lambda pid: pid)
    kills: list[tuple[int, int]] = []
    monkeypatch.setattr(process_identity.os, "killpg", lambda _pgid, sig: kills.append((-1, sig)))
    monkeypatch.setattr(process_identity.os, "kill", lambda pid, sig: kills.append((pid, sig)))
    monkeypatch.setattr(process_identity.time, "sleep", lambda _seconds: None)
    identity = process_identity.RecordedProcessIdentity(
        123,
        123,
        "Fri Jul 3 17:01:02 2026",
        "/usr/bin/python3 /repo/python/cli.py plan-review run",
        "plan-review run",
    )
    responses = [identity, None]

    def fake_read_process_identity(**_kwargs: object) -> process_identity.RecordedProcessIdentity | None:
        return responses.pop(0)

    monkeypatch.setattr(process_identity, "read_process_identity", fake_read_process_identity)
    monkeypatch.setattr(process_identity, "collect_descendants", lambda **_kwargs: (10, 11))
    monkeypatch.setattr(process_identity, "collect_process_group_members", lambda **_kwargs: (11,))

    result = process_identity.terminate_validated_process_group(
        recorded=identity,
        log_path=tmp_path / "kill.jsonl",
        caller="test",
        reason="unit",
    )

    assert result.ok
    assert kills == [
        (-1, process_identity.signal.SIGTERM),
        (10, process_identity.signal.SIGTERM),
        (11, process_identity.signal.SIGTERM),
        (-1, process_identity.signal.SIGKILL),
        (11, process_identity.signal.SIGKILL),
    ]


def test_write_loop_identity_main_retries_until_process_group_stable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    identity = process_identity.RecordedProcessIdentity(
        pid=123,
        pgid=123,
        start_time="Fri Jul 3 17:01:02 2026",
        command_signature="/usr/bin/python3 /repo/python/cli.py plan-review run",
        expected_signature="plan-review run",
    )
    calls: list[int] = []
    responses = [None, identity]

    def fake_read_process_identity(**_kwargs: object) -> process_identity.RecordedProcessIdentity | None:
        calls.append(1)
        return responses.pop(0)

    monkeypatch.setattr(process_identity, "read_process_identity", fake_read_process_identity)
    monkeypatch.setattr(process_identity.time, "sleep", lambda _seconds: None)

    rc = process_identity.write_loop_identity_main([
        "--design-tmpdir",
        str(tmp_path),
        "--pid",
        "123",
    ])

    assert rc == 0
    assert len(calls) == 2
    payload = json.loads((tmp_path / config.DESIGN_STEP3_LOOP_IDENTITY_FILE).read_text(encoding="utf-8"))
    assert payload["pid"] == 123
    assert payload["pgid"] == 123


def test_teardown_loop_identity_main_clears_sidecar_after_validated_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sidecar = tmp_path / config.DESIGN_STEP3_LOOP_IDENTITY_FILE
    sidecar.write_text(
        json.dumps(
            {
                "pid": 123,
                "pgid": 123,
                "start_time": "Fri Jul 3 17:01:02 2026",
                "command_signature": "/usr/bin/python3 /repo/python/cli.py plan-review run",
                "expected_signature": "plan-review run",
            }
        ),
        encoding="utf-8",
    )
    recorded_calls: list[int] = []

    def fake_terminate(*, recorded: process_identity.RecordedProcessIdentity, **_kwargs: object) -> process_identity.ValidationResult:
        recorded_calls.append(recorded.pid)
        return process_identity.ValidationResult(ok=True, reason="ok", current=recorded)

    monkeypatch.setattr(process_identity, "terminate_validated_process_group", fake_terminate)

    rc = process_identity.teardown_loop_identity_main([
        "--design-tmpdir",
        str(tmp_path),
        "--pid",
        "123",
    ])

    assert rc == 0
    assert recorded_calls == [123]
    assert not sidecar.exists()
