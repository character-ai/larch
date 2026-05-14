## Goal
Fix over-greedy larch/sessions expression in redact-tmpdir-paths.sh

## Implementation Plan
## Implementation Plan

### Objective
Fix `scripts/redact-tmpdir-paths.sh` expression 3: add a left boundary anchor
(^|[^[:alnum:]_./-]) so the greedy non-whitespace prefix cannot consume
numeric exit codes, variable names, or other non-path content before a
/larch/sessions/... path.

### Files to modify

1. scripts/redact-tmpdir-paths.sh (line 9)
   - Remove: `'s#[^[:space:]]*/larch/sessions/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#<TMPDIR>#g'`
   - Add: `'s#(^|[^[:alnum:]_./-])/[^[:space:]]*/larch/sessions/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g'`
   The boundary class `[^[:alnum:]_./-]` matches =, ", ', space, :, etc. — 
   all valid pre-path delimiters. `\1` preserves the boundary char.

2. scripts/test-redact-tmpdir-paths.sh — add 4 test cases:
   - E1 (exit code number not consumed): 
     input  = 'Error: Exit code 1\nFoo <TMPDIR>/step3.log'
     expect = 'Error: Exit code 1\nFoo <TMPDIR>/step3.log'
   - E2 (variable-assignment prefix preserved):
     input  = 'export <TMPDIR>/foo'
     expect = 'export IMPLEMENT_TMPDIR=<TMPDIR>/foo'
   - Happy path (space boundary):
     input  = 'Some text <TMPDIR>/foo'
     expect = 'Some text <TMPDIR>/foo'
   - No-match (no /larch/sessions/):
     input  = 'plain text no path here'
     expect = 'plain text no path here'

3. scripts/redact-tmpdir-paths.md — add "Boundary handling" section:
   Document that all three expressions use (^|[^[:alnum:]_./-]) as left
   boundary, and list valid boundary characters (=, ", space, :, etc.).

### Verification
- `bash scripts/test-redact-tmpdir-paths.sh` — all existing + new tests pass
- `/relevant-checks` — clean

## Test plan
(no test plan section in plan-file)
