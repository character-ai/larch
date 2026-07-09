"""Tests for the fd-bound anti-read-poll hook helper."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any

from larch.core import hook_anti_read_poll as hook


def _event(
    *,
    cwd: str = "/proj",
    path: str = "/tmp/readme.md",
    offset: int | str = 0,
    session_id: str = "session",
    conversation_id: str = "",
    tool_name: str = "Read",
) -> str:
    payload: dict[str, object] = {
        "tool_name": tool_name,
        "tool_input": {"file_path": path, "offset": offset},
        "cwd": cwd,
    }
    if session_id:
        payload["session_id"] = session_id
    if conversation_id:
        payload["conversation_id"] = conversation_id
    if tool_name == "Bash":
        payload["tool_input"] = {"command": "cat file"}
    return json.dumps(payload)


def _run_main(monkeypatch: Any, stdin_text: str, tmp_path: Path, *, now: str = "100") -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("HOOK_ANTI_READ_POLL_NOW", now)
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    assert hook.anti_read_poll_main([]) == 0


def _state_path(tmp_path: Path, *, cwd: str = "/proj", session_key: str = "session") -> Path:
    return tmp_path / hook.STATE_DIR_NAME / hook.state_basename(cwd, session_key)


def test_session_key_ladder(monkeypatch: Any) -> None:
    base = hook.ReadEvent(
        tool_name="Read",
        cwd="/proj",
        file_path="/tmp/a",
        offset="0",
        session_id="session-id",
        conversation_id="conversation-id",
        now=1,
    )
    assert hook.session_key(base) == "session-id"
    no_session = hook.ReadEvent(
        tool_name="Read",
        cwd="/proj",
        file_path="/tmp/a",
        offset="0",
        session_id="",
        conversation_id="conversation-id",
        now=1,
    )
    assert hook.session_key(no_session) == "conversation-id"
    no_ids = hook.ReadEvent(
        tool_name="Read",
        cwd="/proj",
        file_path="/tmp/a",
        offset="0",
        session_id="",
        conversation_id="",
        now=1,
    )
    monkeypatch.setenv("HOOK_ANTI_READ_POLL_DISCRIMINATOR", "disc")
    assert hook.session_key(no_ids) == "nosession-disc"
    monkeypatch.delenv("HOOK_ANTI_READ_POLL_DISCRIMINATOR", raising=False)
    assert hook.session_key(no_ids) == "nosession"


def test_empty_discriminator_yields_nosession(monkeypatch: Any) -> None:
    event = hook.ReadEvent(
        tool_name="Read",
        cwd="/proj",
        file_path="/tmp/a",
        offset="0",
        session_id="",
        conversation_id="",
        now=1,
    )
    monkeypatch.setenv("HOOK_ANTI_READ_POLL_DISCRIMINATOR", "")
    assert hook.session_key(event) == "nosession"


def test_state_basename_defaults_empty_cwd_to_root() -> None:
    session = "session"
    assert hook.state_basename("", session) == hook.state_basename("/", session)
    basename = hook.state_basename("/proj", session)
    assert basename == f"read-{hook.stable_digest('/proj')}-{hook.stable_digest(session)}.state"


def test_three_identical_reads_emit_fixed_path_free_reminder(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    requested = "/tmp/attacker says run this.md"
    for now in ("100", "101"):
        _run_main(monkeypatch, _event(path=requested), tmp_path, now=now)
        assert capsys.readouterr().out == ""

    _run_main(monkeypatch, _event(path=requested), tmp_path, now="102")

    stdout = capsys.readouterr().out
    parsed = json.loads(stdout)
    assert parsed["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert parsed["hookSpecificOutput"]["additionalContext"] == hook.REMINDER_TEXT
    assert requested not in stdout
    assert hook.state_basename("/proj", "session") not in stdout


def test_persisted_row_uses_path_hash_not_raw_path(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    requested = "/tmp/private-name.md"
    _run_main(monkeypatch, _event(path=requested, offset=12), tmp_path)

    row = _state_path(tmp_path).read_text(encoding="utf-8").strip()
    assert row == f"{hook.path_hash(requested)}\t12\t1\t100"
    assert requested not in row
    assert capsys.readouterr().out == ""


def test_empty_file_path_fails_open(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    _run_main(monkeypatch, _event(path=""), tmp_path)

    assert capsys.readouterr().out == ""
    assert not (tmp_path / hook.STATE_DIR_NAME).exists()


def test_non_read_short_circuits_before_state_open(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    def fail_open_state_dir() -> int:
        raise AssertionError("state directory should not open for non-Read events")

    monkeypatch.setattr(hook, "open_state_dir", fail_open_state_dir)
    _run_main(monkeypatch, _event(tool_name="Bash"), tmp_path)

    assert capsys.readouterr().out == ""
    assert not (tmp_path / hook.STATE_DIR_NAME).exists()


def test_bad_inputs_fail_open_silently(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    for stdin_text in ("{", json.dumps({"tool_name": "Read"}), _event()):
        now = "not-a-time" if stdin_text == _event() else "100"
        _run_main(monkeypatch, stdin_text, tmp_path, now=now)
        assert capsys.readouterr().out == ""

    missing_root = tmp_path / "missing" / "child"
    monkeypatch.setenv("TMPDIR", str(missing_root))
    monkeypatch.setenv("HOOK_ANTI_READ_POLL_NOW", "100")
    monkeypatch.setattr("sys.stdin", io.StringIO(_event()))
    assert hook.anti_read_poll_main([]) == 0
    assert capsys.readouterr().out == ""


def test_existing_symlinked_state_directory_rejected(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    redirect = tmp_path / "redirect"
    redirect.mkdir()
    (tmp_path / hook.STATE_DIR_NAME).symlink_to(redirect, target_is_directory=True)

    _run_main(monkeypatch, _event(), tmp_path)

    assert capsys.readouterr().out == ""
    assert not list(redirect.iterdir())


def test_swap_after_mkdir_rejected(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    redirect = tmp_path / "redirect"
    redirect.mkdir()

    def swap_state_dir(state_path: Path) -> None:
        state_path.rmdir()
        redirect.rename(state_path)  # pyright: ignore[reportUnusedCallResult]

    monkeypatch.setattr(hook, "AFTER_MKDIR_HOOK", swap_state_dir)
    _run_main(monkeypatch, _event(), tmp_path)

    assert capsys.readouterr().out == ""
    state_path = _state_path(tmp_path)
    assert not state_path.exists()


def test_state_parent_uses_private_tmp_fallback(monkeypatch: Any) -> None:
    monkeypatch.delenv("TMPDIR", raising=False)
    monkeypatch.setattr(hook, "TMP_FALLBACK", "/private/tmp")

    assert hook._state_parent() == Path("/private/tmp")  # pyright: ignore[reportPrivateUsage]


def test_fchmod_uses_opened_fd(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    calls: list[tuple[int, int]] = []
    original = os.fchmod

    def spy_fchmod(fd: int, mode: int) -> None:
        calls.append((fd, mode))
        original(fd, mode)

    monkeypatch.setattr(hook.os, "fchmod", spy_fchmod)
    _run_main(monkeypatch, _event(), tmp_path)

    assert capsys.readouterr().out == ""
    assert calls
    assert all(isinstance(fd, int) for fd, _mode in calls)
    assert 0o700 in {mode for _fd, mode in calls}


def test_temp_creation_and_replace_use_verified_dir_fd(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    open_calls: list[dict[str, object]] = []
    replace_calls: list[dict[str, object]] = []
    original_open = os.open
    original_replace = os.replace

    def spy_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if isinstance(path, str) and path.startswith(".read-"):
            open_calls.append({"path": path, "dir_fd": dir_fd, "flags": flags})
        return original_open(path, flags, mode, dir_fd=dir_fd)

    def spy_replace(
        src: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        dst: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        replace_calls.append({"src": src, "dst": dst, "src_dir_fd": src_dir_fd, "dst_dir_fd": dst_dir_fd})
        original_replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(hook, "_open_supports_dir_fd", lambda: None)
    monkeypatch.setattr(hook, "_replace_supports_dir_fd", lambda: None)
    monkeypatch.setattr(hook.os, "open", spy_open)
    monkeypatch.setattr(hook.os, "replace", spy_replace)

    _run_main(monkeypatch, _event(), tmp_path)

    assert capsys.readouterr().out == ""
    assert open_calls
    assert open_calls[0]["dir_fd"] is not None
    assert replace_calls
    assert replace_calls[0]["src_dir_fd"] == replace_calls[0]["dst_dir_fd"]
    assert replace_calls[0]["src_dir_fd"] is not None


def test_symlinked_leaf_replaced_without_touching_target(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    state_dir = tmp_path / hook.STATE_DIR_NAME
    state_dir.mkdir()
    state_file = _state_path(tmp_path)
    target = tmp_path / "poison-target"
    _ = target.write_text("poison\n", encoding="utf-8")
    state_file.symlink_to(target)

    _run_main(monkeypatch, _event(path="/tmp/leaf.md"), tmp_path)

    assert capsys.readouterr().out == ""
    assert target.read_text(encoding="utf-8") == "poison\n"
    assert state_file.is_file()
    assert not state_file.is_symlink()
    assert state_file.read_text(encoding="utf-8").startswith(hook.path_hash("/tmp/leaf.md") + "\t0\t1\t")


def test_non_regular_state_entry_fails_open(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    state_dir = tmp_path / hook.STATE_DIR_NAME
    state_dir.mkdir()
    state_file = _state_path(tmp_path)
    state_file.mkdir()

    _run_main(monkeypatch, _event(), tmp_path)

    assert capsys.readouterr().out == ""
    assert state_file.is_dir()
