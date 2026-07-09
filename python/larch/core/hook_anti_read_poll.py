"""Advisory PostToolUse hook for repeated Read polling."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
import hashlib
import json
import os
import re
import stat
import sys
import time
from collections.abc import Callable
from typing import cast
from pathlib import Path
from types import TracebackType
from typing import Final, Self
import uuid

from larch.core import config

WINDOW_SECONDS: Final = 30
THRESHOLD_COUNT: Final = 3
STATE_DIR_NAME: Final = "larch-read-poll"
TMP_FALLBACK: Final = "/private/tmp"  # noqa: S108 - hook state contract uses the platform temp root.
REMINDER_TEXT: Final = "Read-poll detected: repeated identical Read calls. Use one read after state changes instead of polling."
SAFE_BASENAME_RE: Final = re.compile(r"^[A-Za-z0-9._-]+$")
_DIGEST_SIZE: Final = 32
_ROW_FIELD_COUNT: Final = 4

AfterMkdirHook = Callable[[Path], None]
AFTER_MKDIR_HOOK: AfterMkdirHook | None = None


class _FailOpen(Exception):
    """Internal sentinel for advisory hook failures."""


@dataclass(frozen=True)
class ReadEvent:
    """Parsed Read hook event fields used for advisory state."""

    tool_name: str
    cwd: str
    file_path: str
    offset: str
    session_id: str
    conversation_id: str
    now: int


@dataclass(frozen=True)
class StateRow:
    """Persisted repeated-read counter row."""

    path_hash: str
    offset: str
    count: int
    epoch: int


class _Fd:
    """Small fd owner used so every opened directory/file is closed."""

    def __init__(self, fd: int) -> None:
        self.fd = fd

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        self.close()

    def release(self) -> int:
        fd = self.fd
        self.fd = -1
        return fd

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


def _nofollow_flag() -> int:
    if not hasattr(os, "O_NOFOLLOW"):
        raise _FailOpen("O_NOFOLLOW unavailable")
    return os.O_NOFOLLOW


def _directory_flag() -> int:
    if not hasattr(os, "O_DIRECTORY"):
        raise _FailOpen("O_DIRECTORY unavailable")
    return os.O_DIRECTORY


def _open_supports_dir_fd() -> None:
    if os.open not in os.supports_dir_fd:
        raise _FailOpen("os.open dir_fd unavailable")


def _replace_supports_dir_fd() -> None:
    if os.replace not in os.supports_dir_fd and os.rename not in os.supports_dir_fd:
        raise _FailOpen("os.replace dir_fd unavailable")


def _dir_open_flags() -> int:
    return os.O_RDONLY | _directory_flag() | _nofollow_flag()


def _read_open_flags() -> int:
    return os.O_RDONLY | _nofollow_flag()


def _write_open_flags() -> int:
    return os.O_WRONLY | os.O_CREAT | os.O_EXCL | _nofollow_flag()


def _validate_entry_name(name: str) -> None:
    if not name or name in {".", ".."} or "/" in name or "\x00" in name or not SAFE_BASENAME_RE.fullmatch(name):
        raise _FailOpen("unsafe state entry name")


def stable_digest(value: str) -> str:
    """Return a stable filesystem-safe digest for hook partition keys."""
    return hashlib.sha256(value.encode("utf-8", "surrogatepass")).hexdigest()[:_DIGEST_SIZE]


def session_key(event: ReadEvent) -> str:
    """Return the shipped session partition key for a parsed hook event."""
    if event.session_id:
        return event.session_id
    if event.conversation_id:
        return event.conversation_id
    discriminator = os.environ.get("HOOK_ANTI_READ_POLL_DISCRIMINATOR", "")
    if discriminator:
        return f"nosession-{discriminator}"
    return "nosession"


def state_basename(cwd: str, resolved_session_key: str) -> str:
    """Return the state filename for a cwd/session partition."""
    cwd_hash = stable_digest(cwd or "/")
    session_hash = stable_digest(resolved_session_key)
    return f"read-{cwd_hash}-{session_hash}.state"


def path_hash(file_path: str) -> str:
    """Return the persisted path digest without exposing the raw path."""
    return stable_digest(file_path)


def _string_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def _offset_value(value: object) -> str:
    raw = str(value) if isinstance(value, int | str) else "0"
    return raw if re.fullmatch(r"-?\d+", raw) else "0"


def _now_value() -> int:
    raw = os.environ.get("HOOK_ANTI_READ_POLL_NOW")
    if raw is None or raw == "":
        return int(time.time())
    if raw.isdigit():
        return int(raw)
    raise _FailOpen("invalid hook time")


def _read_event_from_payload(payload: dict[str, object]) -> ReadEvent:
    tool_input_obj = payload.get("tool_input")
    if not isinstance(tool_input_obj, dict):
        raise _FailOpen("missing tool input")
    tool_input = cast("dict[str, object]", tool_input_obj)
    file_path = _string_value(tool_input.get("file_path"))
    if not file_path:
        raise _FailOpen("missing file path")
    return ReadEvent(
        tool_name="Read",
        cwd=_string_value(payload.get("cwd")) or "/",
        file_path=file_path,
        offset=_offset_value(tool_input.get("offset", 0)),
        session_id=_string_value(payload.get("session_id")),
        conversation_id=_string_value(payload.get("conversation_id")),
        now=_now_value(),
    )


def _decode_payload(stdin_text: str) -> dict[str, object] | None:
    try:
        payload: object = json.loads(stdin_text)
    except json.JSONDecodeError:
        return None
    return cast("dict[str, object]", payload) if isinstance(payload, dict) else None


def parse_stdin_event(stdin_text: str | None = None) -> ReadEvent | None:
    """Parse stdin into a ReadEvent, returning None for fail-open cases."""
    text = sys.stdin.read() if stdin_text is None else stdin_text
    payload = _decode_payload(text)
    if payload is None or _string_value(payload.get("tool_name")) != "Read":
        return None
    try:
        return _read_event_from_payload(payload)
    except _FailOpen:
        return None


def emit_reminder() -> None:
    """Emit the fixed Claude hook reminder envelope."""
    envelope: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": REMINDER_TEXT,
        },
    }
    print(json.dumps(envelope, sort_keys=True, separators=(",", ":")))


def _state_parent() -> Path:
    raw_tmpdir = os.environ.get(config.ENV_TMPDIR) or TMP_FALLBACK
    tmpdir = Path(raw_tmpdir)
    if not tmpdir.is_absolute():
        raise _FailOpen("TMPDIR must be absolute")
    return tmpdir


def _assert_directory_fd(fd: int) -> None:
    fd_stat = os.fstat(fd)
    if not stat.S_ISDIR(fd_stat.st_mode):
        raise _FailOpen("not a directory")


def _open_tmp_root_fd() -> int:
    fd = os.open(_state_parent(), _dir_open_flags())
    try:
        _assert_directory_fd(fd)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _mkdir_state_dir(parent_fd: int) -> None:
    try:
        os.mkdir(STATE_DIR_NAME, 0o700, dir_fd=parent_fd)
    except FileExistsError:
        return


def _assert_same_state_dir(*, parent_fd: int, state_fd: int) -> None:
    state_stat = os.stat(STATE_DIR_NAME, dir_fd=parent_fd, follow_symlinks=False)
    opened_stat = os.fstat(state_fd)
    if not stat.S_ISDIR(state_stat.st_mode) or not stat.S_ISDIR(opened_stat.st_mode):
        raise _FailOpen("state directory changed")
    if (state_stat.st_dev, state_stat.st_ino) != (opened_stat.st_dev, opened_stat.st_ino):
        raise _FailOpen("state directory changed")


def open_state_dir() -> int:
    """Open and verify the fd-bound state directory."""
    _open_supports_dir_fd()
    state_path = _state_parent() / STATE_DIR_NAME
    with _Fd(_open_tmp_root_fd()) as parent:
        _mkdir_state_dir(parent.fd)
        fd = os.open(STATE_DIR_NAME, _dir_open_flags(), dir_fd=parent.fd)
        try:
            _assert_directory_fd(fd)
            if AFTER_MKDIR_HOOK is not None:
                AFTER_MKDIR_HOOK(state_path)
            # Re-check the current path after the seam so a same-UID swap cannot retarget the fd.
            _assert_same_state_dir(parent_fd=parent.fd, state_fd=fd)
            os.fchmod(fd, 0o700)
        except BaseException:
            os.close(fd)
            raise
        return fd


def _parse_row(raw: str) -> StateRow | None:
    fields = raw.rstrip("\n").split("\t")
    if len(fields) != _ROW_FIELD_COUNT:
        return None
    prior_hash, prior_offset, prior_count, prior_epoch = fields
    if not prior_count.isdigit() or not prior_epoch.isdigit():
        return None
    return StateRow(path_hash=prior_hash, offset=prior_offset, count=int(prior_count), epoch=int(prior_epoch))


def _read_regular_file(dir_fd: int, name: str) -> str:
    fd = os.open(name, _read_open_flags(), dir_fd=dir_fd)
    try:
        fd_stat = os.fstat(fd)
        if not stat.S_ISREG(fd_stat.st_mode):
            raise _FailOpen("state leaf is not regular")
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            fd = -1
            return handle.read(512)
    finally:
        if fd >= 0:
            os.close(fd)


def read_state_row(dir_fd: int, name: str) -> StateRow | None:
    """Read a prior state row without following unsafe leaf entries."""
    _validate_entry_name(name)
    try:
        leaf_stat = os.lstat(name, dir_fd=dir_fd)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(leaf_stat.st_mode):
        os.unlink(name, dir_fd=dir_fd)
        return None
    if not stat.S_ISREG(leaf_stat.st_mode):
        raise _FailOpen("state leaf is not regular")
    return _parse_row(_read_regular_file(dir_fd, name))


def _count_for(event: ReadEvent, prior: StateRow | None, event_path_hash: str) -> int:
    if prior is None:
        return 1
    elapsed = event.now - prior.epoch
    same_read = prior.path_hash == event_path_hash and prior.offset == event.offset
    in_window = 0 <= elapsed <= WINDOW_SECONDS
    return prior.count + 1 if same_read and in_window else 1


def _assert_or_unlink_replaceable_destination(dir_fd: int, name: str) -> None:
    try:
        leaf_stat = os.lstat(name, dir_fd=dir_fd)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(leaf_stat.st_mode):
        os.unlink(name, dir_fd=dir_fd)
        return
    if not stat.S_ISREG(leaf_stat.st_mode):
        raise _FailOpen("destination leaf is not regular")


def _write_temp_row(dir_fd: int, temp_name: str, row_text: str) -> None:
    fd = os.open(temp_name, _write_open_flags(), 0o600, dir_fd=dir_fd)
    try:
        fd_stat = os.fstat(fd)
        if not stat.S_ISREG(fd_stat.st_mode):
            raise _FailOpen("temporary leaf is not regular")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            _ = handle.write(row_text)
            handle.flush()
            os.fchmod(handle.fileno(), 0o600)
    finally:
        if fd >= 0:
            os.close(fd)


def write_state_row(dir_fd: int, name: str, row: StateRow) -> None:
    """Atomically write a state row relative to the verified directory fd."""
    _replace_supports_dir_fd()
    _validate_entry_name(name)
    temp_name = f".{name}.tmp.{uuid.uuid4().hex}"
    _validate_entry_name(temp_name)
    replaced = False
    row_text = f"{row.path_hash}\t{row.offset}\t{row.count}\t{row.epoch}\n"
    try:
        _write_temp_row(dir_fd, temp_name, row_text)
        _assert_or_unlink_replaceable_destination(dir_fd, name)
        os.replace(temp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        replaced = True
    finally:
        if not replaced:
            with suppress(FileNotFoundError):
                os.unlink(temp_name, dir_fd=dir_fd)


def _process_event(event: ReadEvent) -> int:
    event_path_hash = path_hash(event.file_path)
    name = state_basename(event.cwd, session_key(event))
    _validate_entry_name(name)
    with _Fd(open_state_dir()) as state_dir:
        prior = read_state_row(state_dir.fd, name)
        count = _count_for(event, prior, event_path_hash)
        write_state_row(
            state_dir.fd,
            name,
            StateRow(path_hash=event_path_hash, offset=event.offset, count=count, epoch=event.now),
        )
    return count


def anti_read_poll_main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the advisory anti-read-poll hook."""
    if argv:
        return 0
    event = parse_stdin_event()
    if event is None:
        return 0
    try:
        count = _process_event(event)
    except Exception:  # pylint: disable=broad-except  # Hook is advisory and must fail open on any local-state failure.
        return 0
    if count == THRESHOLD_COUNT:
        emit_reminder()
    return 0
