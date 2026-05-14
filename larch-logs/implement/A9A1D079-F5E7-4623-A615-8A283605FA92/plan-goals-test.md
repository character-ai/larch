## Goal
Add 4th sed expression to redact-tmpdir-paths.sh to handle \n/path JSONL edge case

## Implementation Plan
Goal: Add a 4th sed expression to scripts/redact-tmpdir-paths.sh so that larch session paths preceded by the JSONL \n escape (two chars: backslash + n) are redacted while preserving the \n prefix.

Root cause: Expression 3 boundary anchor (^|[^[:alnum:]_./-]) can capture \ (backslash), but then expects the next char to be /. When path is \n/Users/..., the char after \ is n (alphanumeric), so expression 3 never matches.

## Implementation Plan

Files to modify (3 files):

1. scripts/redact-tmpdir-paths.sh — append 4th -e expression:
   s#(\\n)/[^[:space:]]*/larch/sessions/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g

2. scripts/test-redact-tmpdir-paths.sh — add 2 test cases:
   - \n immediately before larch/sessions path (no suffix)
   - \n immediately before larch/sessions path (with file suffix)

3. scripts/redact-tmpdir-paths.md — update Boundary handling section to document the \n-prefix carve-out and mention expression 4.

Verification: bash scripts/test-redact-tmpdir-paths.sh — all existing + 2 new tests pass.

## Test plan
(no test plan section in plan-file)
