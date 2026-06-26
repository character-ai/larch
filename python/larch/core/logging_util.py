"""Progress breadcrumbs and JSONL journal (observability only)."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable, Iterator
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO, cast

from larch.core import config
from larch.core import redact

_self_initialized_quiet = False


def reset_quiet_state() -> None:
    """Reset quiet routing state for tests and subprocess re-entry."""
    global _self_initialized_quiet  # noqa: PLW0603
    _self_initialized_quiet = False
    _clear_quiet_env()


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _quiet_disabled() -> bool:
    return _env_truthy(config.ENV_LARCH_QUIET_DISABLE)


def _quiet_active() -> bool:
    return (
        _env_truthy(config.ENV_LARCH_QUIET_ACTIVE)
        and bool(os.environ.get(config.ENV_LARCH_QUIET_PID, ""))
        and not _quiet_disabled()
    )


def _clear_quiet_env() -> None:
    _ = os.environ.pop(config.ENV_LARCH_QUIET_ACTIVE, None)
    _ = os.environ.pop(config.ENV_LARCH_QUIET_PID, None)
    _ = os.environ.pop(config.ENV_LARCH_QUIET_LOG_FILE, None)


def quiet_init(*, argv0: str | None = None) -> None:
    """Initialize quiet-style stdout/stderr routing for this process."""
    global _self_initialized_quiet  # noqa: PLW0603
    if _quiet_disabled():
        return
    active_pid = os.environ.get(config.ENV_LARCH_QUIET_PID, "")
    if _env_truthy(config.ENV_LARCH_QUIET_ACTIVE) and not active_pid:
        return
    if active_pid == str(os.getpid()):
        return
    tmpdir = os.environ.get(config.ENV_DESIGN_TMPDIR, "")
    if not tmpdir or not Path(tmpdir).is_dir():
        tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not tmpdir or not Path(tmpdir).is_dir():
        tmpdir = os.environ.get("TMPDIR", "")
    if not tmpdir or not Path(tmpdir).is_dir():
        tmpdir = "/tmp"  # noqa: S108 - quiet routing parity fallback
    script = Path(argv0 or (sys.argv[0] if sys.argv else "ship.py")).name or "ship.py"
    log_file = os.environ.get(config.ENV_LARCH_QUIET_LOG_FILE, "") or config.PATH_QUIET_LOG_TEMPLATE.format(
        tmpdir=tmpdir,
        script=script,
        pid=os.getpid(),
    )
    try:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Python quiet logs intentionally append for crash/retry forensics,
        # unlike bash larch_quiet_init's truncate-per-initialization contract.
        with path.open("a", encoding="utf-8"):
            pass
        _ = os.dup2(1, 3)
        _ = os.dup2(2, 4)
        log_fd = os.open(path, os.O_WRONLY | os.O_APPEND)
        try:
            _ = os.dup2(log_fd, 1)
            _ = os.dup2(log_fd, 2)
        finally:
            os.close(log_fd)
    except OSError:
        _clear_quiet_env()
        _self_initialized_quiet = False
        return
    os.environ[config.ENV_LARCH_QUIET_ACTIVE] = "1"
    os.environ[config.ENV_LARCH_QUIET_PID] = str(os.getpid())
    os.environ[config.ENV_LARCH_QUIET_LOG_FILE] = log_file
    _self_initialized_quiet = True


def contract_stream() -> TextIO:
    """Return the contract stream: fd 3 after quiet init, else stdout."""
    if _self_initialized_quiet or _quiet_active():
        try:
            return os.fdopen(os.dup(3), "w", encoding="utf-8", closefd=True)
        except OSError:
            return sys.stdout
    return sys.stdout


def emit(text: str) -> None:
    """Write a line to the contract stream (fd 3 after quiet_init, else stdout)."""
    stream = contract_stream()
    line = text if text.endswith("\n") else text + "\n"
    _ = stream.write(line)
    stream.flush()


def sanitize_diagnostic_line(text: str) -> str:
    """Strip C0 control bytes and DEL from one diagnostic line (quiet routing parity)."""
    return "".join(ch for ch in text if ch >= " " and ch != "\x7f")


def sanitize_list(text: str) -> str:
    """Keep only safe characters for comma-separated job KV lists (ci failed-jobs)."""
    return "".join(ch for ch in text if ch.isalnum() or ch in "_,=:-")


def emit_kv(*, key: str, value: str) -> None:
    """Write KEY=value to the contract stream. Raises ValueError on embedded newlines."""
    if "\n" in value or "\r" in value:
        raise ValueError(f"emit_kv value for {key!r} contains newline or carriage-return")
    emit(f"{key}={value}")


def diagnostic(message: str) -> None:
    """Write an operator-visible diagnostic after quiet routing may be active."""
    line = redact.redact_outbound(sanitize_diagnostic_line(message)).rstrip("\n") + "\n"
    if _quiet_active():
        if _self_initialized_quiet:
            with suppress(OSError):
                _ = os.write(4, line.encode("utf-8"))
                return
        else:
            log_file = os.environ.get(config.ENV_LARCH_QUIET_LOG_FILE, "")
            if log_file:
                with suppress(OSError):
                    with Path(log_file).open("a", encoding="utf-8") as handle:
                        _ = handle.write(line)
                    return
    _ = sys.stderr.write(line)
    _ = sys.stderr.flush()


@dataclass(frozen=True)
class BreadcrumbWriter:
    """Progress breadcrumbs; honor quiet routing when LARCH_QUIET_ACTIVE is set."""

    stream: TextIO | None = None

    def emit(self, message: str, *, quiet: bool | None = None) -> None:
        use_quiet = _quiet_active() if quiet is None else quiet
        line = redact.redact_outbound(message).rstrip("\n") + "\n"
        if use_quiet and not _quiet_disabled():
            routed = False
            log_file = os.environ.get(config.ENV_LARCH_QUIET_LOG_FILE, "")
            if log_file:
                with suppress(OSError):
                    with Path(log_file).open("a", encoding="utf-8") as handle:
                        _ = handle.write(line)
                    routed = True
            if _self_initialized_quiet:  # fd 4 is saved stderr only after quiet_init()
                with suppress(OSError):
                    _ = os.write(4, line.encode("utf-8"))
                    routed = True
            if routed or quiet is True:
                return
        stream = self.stream or sys.stderr
        _ = stream.write(line)
        _ = stream.flush()


def iter_jsonl_dicts(lines: Iterable[str]) -> Iterator[dict[str, object]]:
    """Yield JSON object rows from JSONL ``lines``, skipping blank or non-object lines.

    Shared by progress_report and rendering so the parse loop has one definition
    (avoids pylint R0801 duplicate-code across the two modules).
    """
    for line in lines:
        if not line.strip():
            continue
        try:
            parsed: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        yield cast("dict[str, object]", parsed)


@dataclass(frozen=True)
class JsonlJournal:
    """Append-only JSONL journal keyed by run_id."""

    path: Path
    run_id: str

    def append(self, event: str, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {
            "ts": datetime.now(tz=UTC).isoformat(),
            "run_id": self.run_id,
            "event": event,
            **fields,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            _ = handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record
