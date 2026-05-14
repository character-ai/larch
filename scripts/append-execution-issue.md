# append-execution-issue.sh contract

## Purpose

Append one public-safe bullet to a categorized `/implement` execution-issues log. The helper is shared by Mermaid publication guards so sanitizer and assembler failures use the same section insertion logic as prompt-side `/implement` logging.

## Interface

```
append-execution-issue.sh --log <path> --category <category> --entry <bullet>
append-execution-issue.sh --log <path> --category <category> --entry-file <path>
```

Exactly one of `--entry` and `--entry-file` is required. Use `--entry-file` for unbounded captures (multi-MB tool stderr, full CI logs) where argv-sized payloads would risk `E2BIG` or trailing-newline loss from command substitution; the file contents are streamed verbatim into the section without crossing argv.

Supported categories are the exact headers from `skills/implement/SKILL.md`: `Pre-existing Code Issues`, `Tool Failures`, `Permission Prompts`, `External Reviewer Issues`, `CI Issues`, `Warnings`, and `Q/A`.

The script creates the log and parent directory when missing. If the category header exists, the entry is appended under it before the next `###` header; otherwise the category section is appended at the end. Existing sections are preserved.

## Output

On success, stdout is:

```
APPENDED=true
LOG=<path>
```

Failures use `FAILED=true` / `ERROR=<message>` and exit non-zero.

## Conventions

- `set -euo pipefail`.
- Concurrent-safe: a `mkdir "$LOG_FILE.lock.d"` mutex serializes concurrent
  appenders so no entry is lost when multiple callers race on the same log file.
  The lock is released via `trap EXIT` on all exit paths; acquisition is bounded
  to 100 retries (5 s max) before failing with `FAILED=true`.
- Atomic write through sibling temp files and `mv`.
- Multi-line entries are staged in a sibling temp file and read by `awk`;
  callers may pass fenced blocks without newline-collapsing.
- Entries must already be sanitized by the caller; this helper does not redact.

## Edit-in-sync

Update callers in `scripts/sanitize-mermaid-fragment.sh`, `scripts/larch-log.sh`, and Mermaid-related skill prose when changing this contract.
