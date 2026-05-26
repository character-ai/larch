## Decision 1: Scope of issue #2878
- **Question**: Cover both OOS items or just the ADOPTED echo?
- **Resolution**: Both items — ADOPTED echo fix in tracking-issue-read.sh AND a clarifying comment in get-issue-context.sh (no behavior change there).
- **Source**: user (Step 1c)

## Decision 2: Validation-parity direction
- **Question**: Align get-issue-context.sh with lax `case *[!0-9]*` siblings, make all siblings strict, or keep get-issue-context.sh strict and document the divergence?
- **Resolution**: Keep get-issue-context.sh's `^[1-9][0-9]*$` regex (rejects 0 — semantically correct per GitHub). Add a clarifying comment explaining the intentional divergence from siblings. No code change to siblings.
- **Source**: user (Step 1c)

## Decision 3: Test update freedom
- **Question**: Are existing tests for the ADOPTED-invalid path (test-tracking-issue-read-sentinel.sh) free to be updated?
- **Resolution**: Yes — update the assert_contains expectations for the ADOPTED-invalid case to match the new fixed-token error string. Add a regression assertion that no raw value leaks.
- **Source**: user (Step 1c)

## Hard constraints
- The ADOPTED validation must still **reject** invalid values with non-zero exit (current behavior preserved).
- The KV-parsed stdout `FAILED=true` / `ERROR=...` shape must be preserved.
- The redaction must follow the existing `'malformed-value-omitted'` literal used for ISSUE_NUMBER and RUN_ID errors so the three error strings are visually consistent.
