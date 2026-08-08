"""In-process execution-issue ledger helpers the Python /implement steps call.

The `execution-issues` commands themselves are Rust-owned (#8176). What stays
here is the library the still-Python report and guideline paths call directly:
the identity and resolution grammar the final report writes, the chunking and
dedupe keys the guideline append helper must match, and the two mutations that
add and retire one live ledger entry.
"""

# The chunking and dedupe-key helpers below are imported by
# larch.core.architectural_guidelines, whose append helper must match this
# grammar exactly; pyright cannot see that cross-module private import.
# pyright: reportUnusedCallResult=false, reportUnusedFunction=false

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from larch.report import exec_issue_detail
from larch.report.run_log_batch import execution_issue_identity

_RESOLUTION_EVENT = "resolved"


def execution_issue_id(*, category: str, body: str) -> str:
    """Return the stable identity used by append and resolution ledger records."""
    return execution_issue_identity(category=category, body=body)


def execution_issue_resolution_record(*, category: str, entry: str, resolution: str) -> str:
    """Serialize an append-only resolution event for an execution-issue record."""
    return json.dumps({
        "event": _RESOLUTION_EVENT,
        "issue_ids": [execution_issue_id(category=category, body=entry)],
        "resolution": resolution,
    }, separators=(",", ":"), sort_keys=True)


def execution_issue_batch_has_resolution(*, batch_text: str, category: str, entry: str) -> bool:
    """Whether the ledger already records this entry as resolved."""
    issue_id = execution_issue_id(category=category, body=entry)
    for raw in batch_text.splitlines():
        try:
            row: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        row_dict = cast("dict[str, object]", row)
        if row_dict.get("event") != _RESOLUTION_EVENT:
            continue
        issue_ids = row_dict.get("issue_ids")
        if isinstance(issue_ids, list) and issue_id in issue_ids:
            return True
    return False


def _is_fence(line: str) -> bool:
    candidate = line.lstrip()
    if candidate.startswith("- "):
        candidate = candidate[2:].lstrip()
    return candidate.startswith("```")


def _execution_issue_chunks(body: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    in_fence = False
    pending_break = False
    for line in body.splitlines():
        if not in_fence and not line.strip():
            pending_break = bool(current)
            continue
        is_fence = _is_fence(line)
        if not in_fence and line.startswith("- ") and current and not is_fence:
            chunks.append("\n".join(current).strip() + "\n")
            current = []
            pending_break = False
        if pending_break and current:
            chunks.append("\n".join(current).strip() + "\n")
            current = []
        pending_break = False
        current.append(line)
        if is_fence:
            in_fence = not in_fence
    if current:
        chunks.append("\n".join(current).strip() + "\n")
    return chunks


def _execution_issue_body_keys(*, category: str, body: str) -> set[str]:
    return {
        f"{category}\0{key}"
        for key in exec_issue_detail.structured_body_dedupe_keys(body, category)
    }


def _existing_execution_issue_keys(batch_text: str) -> set[str]:
    keys: set[str] = set()
    for raw in batch_text.splitlines():
        try:
            row: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        row_dict = cast("dict[str, object]", row)
        category = row_dict.get("category")
        body = row_dict.get("body")
        if isinstance(category, str) and isinstance(body, str):
            keys.update(_execution_issue_body_keys(category=category, body=body))
    return keys


def append_execution_issue(log: Path, *, category: str, entry: str) -> None:
    if log.is_symlink() or (log.exists() and not log.is_file()):
        raise OSError(f"refusing to append through non-regular log file: {log}")
    text = log.read_text(encoding="utf-8") if log.exists() else ""
    if entry in text:
        return
    heading = f"### {category}"
    lines = text.splitlines()
    section_idx = next((idx for idx, line in enumerate(lines) if line == heading), -1)
    if section_idx < 0:
        text = text.rstrip() + ("\n\n" if text.strip() else "") + f"{heading}\n{entry}\n"
    else:
        insert_idx = len(lines)
        for idx in range(section_idx + 1, len(lines)):
            if lines[idx].startswith("### "):
                insert_idx = idx
                break
        while insert_idx > section_idx + 1 and lines[insert_idx - 1] == "":
            insert_idx -= 1
        lines.insert(insert_idx, entry)
        text = "\n".join(lines).rstrip() + "\n"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(text, encoding="utf-8")


def resolve_execution_issue(log: Path, *, entry: str) -> bool:
    """Remove an open entry from the mutable log after its durable resolution.

    Committed batches remain append-only: callers first append
    :func:`execution_issue_resolution_record`, then use this helper to prevent a
    still-live copy from being merged back into the final report.
    """
    if log.is_symlink() or (log.exists() and not log.is_file()):
        raise OSError(f"refusing to resolve through non-regular log file: {log}")
    if not log.is_file():
        return False
    lines = log.read_text(encoding="utf-8").splitlines()
    try:
        lines.remove(entry)
    except ValueError:
        return False
    text = "\n".join(lines).rstrip() + "\n"
    log.write_text(text, encoding="utf-8")
    return True
