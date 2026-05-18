#!/usr/bin/env python3
"""Audit runtime session transcripts for prompt cache-key drift.

Reads larch implement run logs and compares the stable prefix material seen by
consecutive assistant API requests. Canonical contract:
scripts/cache-key-runtime-audit.md.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_RUNS = 10
DEFAULT_MAX_DIFF_CHARS = 2000


def stable_json_text(value: Any) -> str:
    return json.dumps(
        stable_json(value),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def summarize_attachment_block(item: dict[str, Any]) -> str:
    summary = {
        "type": str(item.get("type") or "unknown"),
        "payload_sha256": digest_text(stable_json_text(item)),
    }
    return json.dumps(summary, sort_keys=True, ensure_ascii=False)


@dataclass(frozen=True)
class TranscriptEntry:
    index: int
    path: Path
    raw: dict[str, Any]

    @property
    def uuid(self) -> str:
        return str(self.raw.get("uuid") or "")

    @property
    def parent_uuid(self) -> str:
        return str(self.raw.get("parentUuid") or "")

    @property
    def entry_type(self) -> str:
        return str(self.raw.get("type") or "")


@dataclass(frozen=True)
class PrefixRecord:
    kind: str
    uuid: str
    label: str
    content: str

    def render(self) -> str:
        return f"### {self.label}\n{self.content}\n"


@dataclass(frozen=True)
class TurnAudit:
    turn: int
    assistant_uuid: str
    request_id: str
    timestamp: str
    classification: str
    reason: str
    stable_hash: str
    stable_records: list[PrefixRecord]
    diff: str


@dataclass(frozen=True)
class RunAudit:
    run_id: str
    transcript_path: Path
    parsed_entries: int
    invalid_lines: int
    assistant_requests: int
    turns: list[TurnAudit]
    warnings: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit larch implement session transcripts for prompt cache-key drift."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help=f"number of most recent runs with transcripts to audit (default: {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--log-root",
        default="larch-logs/implement",
        help="root containing implement run directories (default: larch-logs/implement)",
    )
    parser.add_argument(
        "--max-diff-chars",
        type=int,
        default=DEFAULT_MAX_DIFF_CHARS,
        help=f"maximum diff characters per finding (default: {DEFAULT_MAX_DIFF_CHARS})",
    )
    return parser.parse_args()


def content_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                block_type = str(item.get("type") or "")
                if block_type not in ("", "text"):
                    parts.append(summarize_attachment_block(item))
                elif "text" in item and isinstance(item["text"], str):
                    parts.append(item["text"])
                elif "content" in item:
                    parts.append(content_to_text(item["content"]))
                else:
                    parts.append(stable_json_text(item))
            else:
                parts.append(content_to_text(item))
        return "\n".join(part for part in parts if part != "")
    if isinstance(value, dict):
        block_type = str(value.get("type") or "")
        if block_type not in ("", "text"):
            return summarize_attachment_block(value)
        if "text" in value and isinstance(value["text"], str):
            return value["text"]
        if "content" in value:
            return content_to_text(value["content"])
        return stable_json_text(value)
    return str(value)


def entry_content(entry: TranscriptEntry) -> str:
    raw = entry.raw
    if entry.entry_type == "attachment" and "attachment" in raw:
        return content_to_text(raw.get("attachment"))
    message = raw.get("message")
    if isinstance(message, dict) and "content" in message:
        return content_to_text(message.get("content"))
    if "content" in raw:
        return content_to_text(raw.get("content"))
    return stable_json_text(raw)


def stable_json(value: Any) -> Any:
    """Return JSON content without volatile envelope fields."""
    volatile = {
        "cwd",
        "durationMs",
        "entrypoint",
        "gitBranch",
        "sessionId",
        "timestamp",
        "toolUseID",
        "userType",
        "uuid",
        "parentUuid",
        "version",
    }
    if isinstance(value, dict):
        return {
            str(key): stable_json(item)
            for key, item in value.items()
            if str(key) not in volatile
        }
    if isinstance(value, list):
        return [stable_json(item) for item in value]
    return value


def read_transcript(path: Path) -> tuple[list[TranscriptEntry], int]:
    entries: list[TranscriptEntry] = []
    invalid_lines = 0
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if isinstance(parsed, dict):
                entries.append(TranscriptEntry(index=index, path=path, raw=parsed))
            else:
                invalid_lines += 1
    return entries, invalid_lines


def run_sort_key(run_dir: Path) -> tuple[str, float, str]:
    manifest = run_dir / "manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        updated = str(data.get("updated_at") or data.get("started_at") or "")
        if updated:
            return (updated, 0.0, run_dir.name)
    transcript = run_dir / "session-transcript.jsonl"
    try:
        mtime = transcript.stat().st_mtime
    except OSError:
        mtime = 0.0
    return ("", mtime, run_dir.name)


def select_transcripts(log_root: Path, runs: int) -> list[Path]:
    if runs <= 0:
        raise ValueError("--runs must be greater than zero")
    if not log_root.exists():
        raise FileNotFoundError(f"log root not found: {log_root}")
    run_dirs = [
        path
        for path in log_root.iterdir()
        if path.is_dir() and (path / "session-transcript.jsonl").is_file()
    ]
    run_dirs.sort(key=run_sort_key, reverse=True)
    return [path / "session-transcript.jsonl" for path in run_dirs[:runs]]


def unique_assistant_requests(entries: list[TranscriptEntry]) -> list[TranscriptEntry]:
    seen: set[str] = set()
    result: list[TranscriptEntry] = []
    for entry in entries:
        if entry.entry_type != "assistant":
            continue
        message = entry.raw.get("message")
        message_id = message.get("id") if isinstance(message, dict) else ""
        request_id = str(
            entry.raw.get("requestId")
            or message_id
            or entry.uuid
        )
        if request_id in seen:
            continue
        seen.add(request_id)
        result.append(entry)
    return result


def chain_to_root(
    entry: TranscriptEntry,
    by_uuid: dict[str, TranscriptEntry],
) -> tuple[list[TranscriptEntry], str | None]:
    chain: list[TranscriptEntry] = []
    seen: set[str] = set()
    parent_uuid = entry.parent_uuid
    while parent_uuid:
        if parent_uuid in seen:
            chain.reverse()
            return chain, parent_uuid
        seen.add(parent_uuid)
        parent = by_uuid.get(parent_uuid)
        if parent is None:
            chain.reverse()
            return chain, parent_uuid
        chain.append(parent)
        parent_uuid = parent.parent_uuid
    chain.reverse()
    return chain, None


def is_initial_user_message(entry: TranscriptEntry, before_first_assistant: bool) -> bool:
    if not before_first_assistant or entry.entry_type != "user":
        return False
    content = entry_content(entry)
    if "tool_use_id" in content or "tool_result" in content:
        return False
    return True


def _is_attachment_bearing(entry: TranscriptEntry) -> bool:
    """Return True if entry content has any non-text attachment blocks."""
    raw = entry.raw
    message = raw.get("message")
    content = (
        message.get("content") if isinstance(message, dict)
        else raw.get("content")
    )
    if isinstance(content, dict):
        return str(content.get("type") or "") not in ("", "text")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and str(block.get("type") or "") not in ("", "text"):
                return True
    return False


def prefix_records(chain: list[TranscriptEntry]) -> list[PrefixRecord]:
    records: list[PrefixRecord] = []
    # chain comes from chain_to_root which walks parent->grandparent and never
    # contains assistant entries (the walk starts at assistant.parent_uuid).
    # Track whether we already included the one allowed user:initial record so
    # subsequent non-tool user bubbles are not treated as part of the stable prefix.
    included_initial = False
    for entry in chain:
        if entry.entry_type == "assistant":
            continue
        include = False
        kind = entry.entry_type
        reason = kind
        if entry.entry_type == "system":
            include = True
            reason = f"system:{entry.raw.get('subtype') or 'unknown'}"
        elif entry.entry_type == "attachment":
            include = True
            attachment = entry.raw.get("attachment")
            attachment_type = ""
            if isinstance(attachment, dict):
                attachment_type = str(attachment.get("type") or "")
            reason = f"attachment:{attachment_type or 'unknown'}"
        elif entry.entry_type == "user" and entry.raw.get("isMeta") is True:
            include = True
            reason = "user:isMeta"
        elif entry.entry_type == "user" and _is_attachment_bearing(entry):
            include = True
            reason = "user:attachment"
            included_initial = True
        elif not included_initial and is_initial_user_message(entry, True):
            include = True
            reason = "user:initial"
            included_initial = True
        if not include:
            continue
        records.append(
            PrefixRecord(
                kind=reason,
                uuid=entry.uuid,
                label=f"{reason} {entry.uuid or f'line:{entry.index}'}",
                content=entry_content(entry),
            )
        )
    return records


def digest_records(records: list[PrefixRecord]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(b"\x1e")
        digest.update(record.label.encode("utf-8", errors="replace"))
        digest.update(b"\n")
        digest.update(record.content.encode("utf-8", errors="replace"))
        digest.update(b"\n")
    return digest.hexdigest()


def render_records(records: list[PrefixRecord]) -> list[str]:
    lines: list[str] = []
    for record in records:
        lines.extend(record.render().splitlines(keepends=True))
    return lines


def truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... diff truncated at {max_chars} chars ...\n"


def diff_records(
    previous: list[PrefixRecord],
    current: list[PrefixRecord],
    max_chars: int,
) -> str:
    diff = difflib.unified_diff(
        render_records(previous),
        render_records(current),
        fromfile="previous-stable-prefix",
        tofile="current-stable-prefix",
        lineterm="",
    )
    return truncate("\n".join(diff), max_chars)


def exact_prefix(
    previous: list[PrefixRecord],
    current: list[PrefixRecord],
) -> bool:
    if len(previous) > len(current):
        return False
    for left, right in zip(previous, current):
        if left != right:
            return False
    return True


def classify_change(
    previous: list[PrefixRecord],
    current: list[PrefixRecord],
) -> tuple[str, str]:
    if previous == current:
        return ("EXPECTED-GROWTH", "stable prefix unchanged")
    if exact_prefix(previous, current):
        added = current[len(previous) :]
        if any(record.kind == "user:isMeta" for record in added):
            return ("EXPECTED-GROWTH", "new isMeta prompt content loaded")
        if added and all(record.kind.startswith("system:") for record in added):
            return ("EXPECTED-CHANGE", "runtime system entries appended")
        return ("EXPECTED-GROWTH", "stable prefix extended")

    shared = min(len(previous), len(current))
    changed: list[tuple[PrefixRecord, PrefixRecord]] = []
    for index in range(shared):
        if previous[index] != current[index]:
            changed.append((previous[index], current[index]))
    system_only = bool(changed) and all(
        left.kind.startswith("system:") and right.kind.startswith("system:")
        for left, right in changed
    )
    if system_only:
        return ("EXPECTED-CHANGE", "runtime system content changed")

    changed_labels = ", ".join(
        sorted({left.label for left, _ in changed} | {right.label for _, right in changed})
    )
    if not changed_labels:
        changed_labels = "stable prefix record set changed"
    return ("CACHE-INVALIDATING", f"stable prefix content changed: {changed_labels}")


def audit_run(path: Path, max_diff_chars: int) -> RunAudit:
    entries, invalid_lines = read_transcript(path)
    by_uuid = {entry.uuid: entry for entry in entries if entry.uuid}
    assistants = unique_assistant_requests(entries)
    warnings: list[str] = []
    turns: list[TurnAudit] = []
    previous_records: list[PrefixRecord] | None = None
    previous_hash = ""

    for turn_index, assistant in enumerate(assistants, 1):
        chain, broken_parent = chain_to_root(assistant, by_uuid)
        if broken_parent:
            warnings.append(
                f"turn {turn_index}: parent chain stopped at missing/cyclic uuid {broken_parent}"
            )
        records = prefix_records(chain)
        stable_hash = digest_records(records)
        if previous_records is None:
            classification = "BASELINE"
            reason = "first assistant request"
            diff = ""
        elif broken_parent:
            # Incomplete chain: prefix may be shorter than reality, so a
            # content change could be a chain artefact rather than real drift.
            classification = "INCONCLUSIVE"
            reason = f"incomplete parent chain (stopped at {broken_parent})"
            diff = ""
        elif stable_hash == previous_hash:
            classification = "EXPECTED-GROWTH"
            reason = "stable prefix hash unchanged"
            diff = ""
        else:
            classification, reason = classify_change(previous_records, records)
            diff = diff_records(previous_records, records, max_diff_chars)

        turns.append(
            TurnAudit(
                turn=turn_index,
                assistant_uuid=assistant.uuid,
                request_id=str(assistant.raw.get("requestId") or ""),
                timestamp=str(assistant.raw.get("timestamp") or ""),
                classification=classification,
                reason=reason,
                stable_hash=stable_hash,
                stable_records=records,
                diff=diff,
            )
        )
        previous_records = records
        previous_hash = stable_hash

    return RunAudit(
        run_id=path.parent.name,
        transcript_path=path,
        parsed_entries=len(entries),
        invalid_lines=invalid_lines,
        assistant_requests=len(assistants),
        turns=turns,
        warnings=warnings,
    )


def render_report(audits: list[RunAudit]) -> str:
    total_turns = sum(audit.assistant_requests for audit in audits)
    total_comparisons = sum(max(0, audit.assistant_requests - 1) for audit in audits)
    total_invalidating = sum(
        1
        for audit in audits
        for turn in audit.turns
        if turn.classification == "CACHE-INVALIDATING"
    )
    total_expected_change = sum(
        1
        for audit in audits
        for turn in audit.turns
        if turn.classification == "EXPECTED-CHANGE"
    )
    reusable = total_comparisons - total_invalidating
    efficiency = 100.0 if total_comparisons == 0 else (reusable / total_comparisons) * 100

    lines = [
        "# Runtime Cache-Key Audit",
        "",
        "## Summary",
        "",
        f"- Runs audited: {len(audits)}",
        f"- Assistant API requests: {total_turns}",
        f"- Turn-to-turn comparisons: {total_comparisons}",
        f"- CACHE-INVALIDATING findings: {total_invalidating}",
        f"- EXPECTED-CHANGE comparisons: {total_expected_change}",
        f"- Cache-efficient comparisons: {efficiency:.1f}%",
        "",
    ]

    for audit in audits:
        invalidating = [
            turn for turn in audit.turns if turn.classification == "CACHE-INVALIDATING"
        ]
        expected_change = [
            turn for turn in audit.turns if turn.classification == "EXPECTED-CHANGE"
        ]
        inconclusive = [
            turn for turn in audit.turns if turn.classification == "INCONCLUSIVE"
        ]
        comparisons = max(0, audit.assistant_requests - 1)
        run_efficiency = (
            100.0
            if comparisons == 0
            else ((comparisons - len(invalidating)) / comparisons) * 100
        )
        lines.extend(
            [
                f"## Run {audit.run_id}",
                "",
                f"- Transcript: `{audit.transcript_path}`",
                f"- Parsed entries: {audit.parsed_entries}",
                f"- Invalid NDJSON lines skipped: {audit.invalid_lines}",
                f"- Assistant API requests: {audit.assistant_requests}",
                f"- CACHE-INVALIDATING findings: {len(invalidating)}",
                f"- EXPECTED-CHANGE comparisons: {len(expected_change)}",
                f"- INCONCLUSIVE turns (broken parent chain): {len(inconclusive)}",
                f"- Cache-efficient comparisons: {run_efficiency:.1f}%",
                "",
            ]
        )
        if audit.warnings:
            lines.append("### Warnings")
            lines.append("")
            for warning in audit.warnings:
                lines.append(f"- {warning}")
            lines.append("")
        findings = invalidating + expected_change
        if not findings:
            lines.extend(["No cache-invalidating or expected-change findings.", ""])
            continue
        for turn in findings:
            lines.extend(
                [
                    f"### Turn {turn.turn}: {turn.classification}",
                    "",
                    f"- Reason: {turn.reason}",
                    f"- Request ID: `{turn.request_id or 'unknown'}`",
                    f"- Assistant UUID: `{turn.assistant_uuid or 'unknown'}`",
                    f"- Timestamp: `{turn.timestamp or 'unknown'}`",
                    f"- Stable prefix SHA256: `{turn.stable_hash}`",
                    "",
                ]
            )
            if turn.diff:
                lines.extend(["```diff", turn.diff, "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    log_root = Path(args.log_root)
    try:
        transcripts = select_transcripts(log_root, args.runs)
    except (FileNotFoundError, ValueError) as exc:
        print(f"cache-key-runtime-audit: {exc}", file=sys.stderr)
        return 2

    audits = [audit_run(path, args.max_diff_chars) for path in transcripts]
    if not audits:
        print(f"cache-key-runtime-audit: no session-transcript.jsonl files under {log_root}")
        return 0
    print(render_report(audits), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
