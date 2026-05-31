"""Progress breadcrumbs and JSONL journal (observability only)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

import config


def _quiet_disabled() -> bool:
    return os.environ.get(config.ENV_LARCH_QUIET_DISABLE, "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass
class BreadcrumbWriter:
    """stderr breadcrumb stream; suppressed when quiet is active."""

    stream: TextIO = sys.stderr

    def emit(self, message: str, *, quiet: bool = False) -> None:
        if quiet and not _quiet_disabled():
            return
        _ = self.stream.write(message.rstrip("\n") + "\n")
        _ = self.stream.flush()


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
