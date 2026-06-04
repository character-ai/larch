"""Progress breadcrumbs and JSONL journal (observability only)."""

from __future__ import annotations

import json
import os
import sys
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

import config
import redact


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


@dataclass
class BreadcrumbWriter:
    """Progress breadcrumbs; honor lib-quiet routing when LARCH_QUIET_ACTIVE is set."""

    stream: TextIO | None = None

    def emit(self, message: str, *, quiet: bool | None = None) -> None:
        use_quiet = _quiet_active() if quiet is None else quiet
        line = redact.redact_outbound(message).rstrip("\n") + "\n"
        if use_quiet and not _quiet_disabled():
            routed = False
            log_file = os.environ.get(config.ENV_LARCH_QUIET_LOG_FILE, "")
            if log_file:
                with Path(log_file).open("a", encoding="utf-8") as handle:
                    _ = handle.write(line)
                routed = True
            with suppress(OSError):
                _ = os.write(4, line.encode("utf-8"))
                routed = True
            if routed or quiet is True:
                return
        stream = self.stream or sys.stderr
        _ = stream.write(line)
        _ = stream.flush()


@dataclass
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
