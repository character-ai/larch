# Discussion Round 1 — Decisions

## Decision 1: Scope — both sub-fixes in one plan
- **Question**: Should both sub-fixes (CI fix-agent prompt grounding for topology drift + regression test for vendor-loop-exhausted exit code + final-bail-reason.txt preservation) ship in one plan, or split into separate issues?
- **Resolution**: Both in one plan. They share a root cause (ship-pr CI-fix failure on #2668) and the diff is small.
- **Source**: user

## Decision 2: Diagnose then fix the exit-3 gap
- **Question**: Should we diagnose the actual root cause of the exit-3 anomaly before designing the fix, or just add the regression test for the documented exit-4 path and treat exit-3 as a separate investigation?
- **Resolution**: Diagnose first. Codebase investigation revealed exit 3 is effectively unreachable in production: no real BAIL_REASON producer emits the exact-match tokens (`fix-attempts-exhausted|design-flaw|escalate|all-vendors-failed`) that `needs_user_bail_reason` requires. `ci-decide.sh` emits free-form prose like `Too many fix attempts (10) without CI passing` that does not match. `/implement` Step 16 (SKILL.md:1595) still treats exit 3 as an active contract value.
- **Source**: user (decision) + codebase (diagnosis)

## Decision 3: final-bail-reason.txt persistence approach
- **Question**: How should `final-bail-reason.txt` be preserved long enough to aid diagnosis in future incidents?
- **Resolution**: Copy it to the committed `larch-logs/implement/<RUN_ID>/` run-log via a new larch-log batch slug. Survives across runs since the run log is committed.
- **Source**: user

## Decision 4: Exit-3 disposition — wire FIX_ATTEMPTS cap to exit 3
- **Question**: Given exit 3 is unreachable, should the fix make it reachable, keep the stub with a negative regression test, or replace exact-match with substring matching?
- **Resolution**: Make `ci-decide.sh` emit `BAIL_REASON=fix-attempts-exhausted` (exact-match) when `FIX_ATTEMPTS >= 10`, so the exit-3 path becomes reachable. Existing human-readable note moves to an adjacent line. Closes the dead-path gap AND keeps the `/implement` exit-3 contract intact.
- **Source**: user

## Decision 5: Regression test approach for vendor-loop exhaustion
- **Question**: How should the regression test exercise the vendor-fix-loop-exhausted path?
- **Resolution**: Stub `launch-cursor-ci.sh` / `launch-codex-ci.sh` / `launch-claude-ci.sh` to all return non-zero in a new `test-ship-pr.sh` block; assert ship-pr exits 4 via `exit_stall "10-max-retries"`. Matches existing stub-harness style.
- **Source**: user

## Hard constraints (in-scope-but-immutable)
- The exit-code contract MUST be preserved: `/implement` Step 16 (SKILL.md:1595) reads exit 3 as "user-input bail" and routes via Step 12d. Exit 4 = stall.
- `BAIL_REASON` values added to `ci-decide.sh` must remain single-line strings; `ship-pr.sh` line 601 truncates to first line / 200 chars.
- The CI-fix-agent prompt parity rule (`.claude/rules/external-tool-launcher-parity.md`) applies: any prompt-text change in `launch-cursor-ci.sh` must mirror in `launch-codex-ci.sh` and `launch-claude-ci.sh`.

## Non-goals
- Refactoring `ship-pr.sh` state machine
- Changing the existing 3-tier vendor waterfall (Cursor → Codex → Claude)
- Removing or changing the existing test at `test-ship-pr.sh:1042-1047`
