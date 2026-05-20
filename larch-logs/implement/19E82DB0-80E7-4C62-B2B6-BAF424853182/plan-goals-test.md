## Goal
Suppress transient CI-still-in-progress polling entries from execution-issues.ndjson by adding exit code 2 to gh-run-logs.sh and filtering it in the caller

## Implementation Plan

### Files to modify

1. scripts/gh-run-logs.sh — Detect "still in progress" output and exit 2.
   Replace the bare pipe `gh run view ... | tail -100` with a capture pattern:
   - `gh_rc=0; raw=$(gh run view "$RUN_ID" --repo "$REPO" --log-failed 2>&1) || gh_rc=$?`
   - If `gh_rc != 0` AND raw contains "is still in progress; logs will be available": exit 2
   - Otherwise: `printf '%s\n' "$raw" | tail -100; exit "$gh_rc"`

2. scripts/gh-run-logs.md — Add exit code 2 to the documented contract.

3. scripts/ship-pr.sh line ~1197 — Skip record_failure when rc=2:
   Change `[ "$rc" -eq 0 ] || record_failure ...`
   To     `[ "$rc" -eq 0 ] || [ "$rc" -eq 2 ] || record_failure ...`

### Files to create

4. scripts/test-gh-run-logs.sh — Unit test:
   - Stub `gh` to output "run X is still in progress; logs will be available when it is complete" and exit 1
   - Assert gh-run-logs.sh exits 2
   - Stub `gh` to output normal log lines and exit 0
   - Assert gh-run-logs.sh exits 0
   - Stub `gh` to output unrelated error and exit 1
   - Assert gh-run-logs.sh exits 1

5. scripts/test-gh-run-logs.md — Sibling stub pointing to gh-run-logs.md.

### Edge cases

- `gh run view --log-failed` writes "still in progress" to either stdout or stderr;
  the fix uses `2>&1` in the command substitution to capture both streams.
- The `set -euo pipefail` in gh-run-logs.sh requires `|| gh_rc=$?` to prevent
  the assignment from triggering set-e on non-zero.
- exit "$gh_rc" at the end preserves the exact gh exit code for non-in-progress failures.

### Testing strategy

Run `bash scripts/test-gh-run-logs.sh` — it stubs `gh` and validates all three
exit code scenarios. No live GitHub API needed.

## Test plan
(no test plan section in plan-file)
