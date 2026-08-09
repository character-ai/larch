"""Shared owner for typed open-issue rows and JSON helpers.

``open_issue_rows_read`` centralizes the ``gh issue list`` open-state read plus
tolerant row normalization into frozen :class:`OpenIssueRow` values for the
remaining Python migration-governance consumer. ``load_json_file``,
``positive_int_value``, and ``emit_json`` remain its file-input,
number-parsing, and JSON-emit helpers.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from larch.core import proc
from larch.git import gh

# Field set and large limit both current callers passed to ``gh.issue_list_read``.
ISSUE_LIST_FIELDS = ("number", "title", "state", "labels", "body")
ISSUE_LIST_LIMIT = 100000


def emit_json(payload: dict[str, Any]) -> int:
    json.dump(payload, sys.stdout, sort_keys=True)
    _ = sys.stdout.write("\n")
    return 0


def load_json_file(path: str, *, desc: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{desc}: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{desc}: invalid JSON: {exc}") from exc


def positive_int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return int(value)
    return None


def _label_name(item: Any) -> str:
    name = cast("dict[str, Any]", item).get("name") if isinstance(item, dict) else item
    return str(name) if name else ""


def _label_names(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(name for name in map(_label_name, cast("list[Any]", value)) if name)


@dataclass(frozen=True)
class OpenIssueRow:
    """One open GitHub issue, normalized for the combine and deps consumers."""

    number: int
    title: str
    state: str
    labels: tuple[str, ...]
    body: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "state": self.state,
            "labels": list(self.labels),
            "body": self.body,
        }


def parse_open_issue_row(row: Any) -> OpenIssueRow | None:
    """Return a normalized open row, or ``None`` for malformed or non-open input.

    Skip policy (never raises): drop non-dict rows, rows without a positive
    integer ``number`` (``bool`` never counts as positive), and rows whose
    ``state`` is not ``open`` (case-insensitive). Both current callers skip such
    rows rather than failing the whole read. Missing ``title``/``labels``/``body``
    normalize to empty; labels reduce to a tuple of their names.
    """
    if not isinstance(row, dict):
        return None
    data = cast("dict[str, Any]", row)
    number = positive_int_value(data.get("number"))
    if number is None:
        return None
    if str(data.get("state") or "").casefold() != "open":
        return None
    return OpenIssueRow(
        number=number,
        title=str(data.get("title") or ""),
        state="open",
        labels=_label_names(data.get("labels")),
        body=str(data.get("body") or ""),
    )


def open_issue_rows_read(runner: proc.Runner, *, repo: str) -> tuple[OpenIssueRow, ...]:
    """Return ``repo``'s open issues as immutable typed rows sorted by number.

    Reads through :func:`larch.git.gh.issue_list_read` with the shared field set
    and large limit, drops malformed and non-open rows, and normalizes labels to
    a tuple of names. ``ShipError`` raised by the wrapper (gh failure or invalid
    JSON) propagates unchanged so each caller formats its own diagnostics.
    """
    rows = gh.issue_list_read(
        runner,
        repo=repo,
        state="open",
        fields=ISSUE_LIST_FIELDS,
        limit=ISSUE_LIST_LIMIT,
    )
    parsed = [row for row in map(parse_open_issue_row, rows) if row is not None]
    return tuple(sorted(parsed, key=lambda item: item.number))
