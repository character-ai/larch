## Goal
Add compose-collector-failure-log.sh to guarantee non-empty execution-issues entries for STATUS=EMPTY_OUTPUT collector failures in /design plan-review

## Implementation Plan

### Goal
Add `scripts/compose-collector-failure-log.sh` + sibling `.md` + test harness, and update `skills/design/references/plan-review.md` line 9 to use a deterministic Bash recipe instead of prose. This ensures every non-OK collector status produces a non-empty `execution-issues.md` entry.

### Files

1. **`scripts/compose-collector-failure-log.sh`** (new, executable)
   - Args: `--reviewer-file <path>`, `--structured-record <record-line>`, `--output <path>`
   - Validates: `--structured-record` non-empty → exit 2; `--output` parent missing → exit 2
   - Writes output atomically via `mktemp` + `mv`: three sections — structured record, reviewer output, reviewer stderr (.diag)
   - Sections use `(empty: <path>)` / `(file missing: <path>)` placeholders for empty/absent files
   - Guaranteed non-empty (structured record always written first)
   - Standard preamble: `#!/usr/bin/env bash`, `set -euo pipefail`, `source lib-quiet.sh`, `larch_quiet_init`

2. **`scripts/compose-collector-failure-log.md`** (new)
   - Purpose, primary callers, invariants, harness, edit-in-sync note

3. **`scripts/test-compose-collector-failure-log.sh`** (new, executable)
   - 10 test cases as specified in the issue
   - Pattern: `LARCH_QUIET_DISABLE=1`, `REPO_ROOT`, `cleanup()`, `ok()`/`fail()` helpers, `PASS_COUNT`/`FAIL_COUNT`
   - Wired into Makefile (shard assignment TBD after checking existing shard sizes)

4. **`skills/design/references/plan-review.md`** (edit, line 9)
   - Replace the prose failure-logging block with explicit Bash recipe block for non-OK collector statuses
   - Keep the prose intro sentence, replace composition instruction with the new helper call

### Approach

A. Write the script following the exact interface and behavior in the issue sketch.
B. Write a concise sibling `.md`.
C. Write the 10-case test harness.
D. Edit plan-review.md line 9 to add the recipe block.
E. Wire harness into Makefile in an appropriate shard.

### Edge cases
- `--structured-record` given but with embedded newlines: treat as valid (the whole record, possibly multi-line, goes into the structured-record section)
- `--reviewer-file` argument empty string (not provided): `dump_section` receives empty path → `(no path provided)`
- `--output` parent exists as a file (not directory): `[[ -d "$(dirname "$OUTPUT")" ]]` check catches it → exit 2
- Atomic write: `mktemp` in `$TMPDIR` then `mv` to `$OUTPUT`; if `cat` hangs mid-compose, only the tmpfile is partial


## Test plan
- `bash scripts/test-compose-collector-failure-log.sh` passes all 10 cases
- `bash scripts/test-design-structure.sh` still passes
- `/relevant-checks` green
