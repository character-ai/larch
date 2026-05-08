# append-execution-issue.sh contract

## Purpose

Append one public-safe bullet to a categorized `/implement` execution-issues log. The helper is shared by Mermaid publication guards so sanitizer and assembler failures use the same section insertion logic as prompt-side `/implement` logging.

## Interface

```
append-execution-issue.sh --log <path> --category <category> --entry <bullet>
```

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
- Atomic write through a sibling temp file and `mv`.
- Entries must already be sanitized by the caller; this helper does not redact.

## Edit-in-sync

Update callers in `scripts/sanitize-mermaid-fragment.sh`, `scripts/assemble-anchor.sh`, and Mermaid-related skill prose when changing this contract.
