## Decision 1: Failure-detection scope for `reuse_slot_result`
- **Question**: Should the fix cover only "source file missing" or all `cp` failure modes?
- **Resolution**: All `cp` failure modes (per Step 1c clarification). Any non-zero `cp` exit causes reuse to be skipped; the caller falls through to relaunch.
- **Source**: user

## Decision 2: Regression test coverage
- **Question**: Should the design include a regression test?
- **Resolution**: Yes — extend `scripts/test-dispatch-with-waterfall.sh` with a scenario that constructs a group ledger row whose `output_path` points at a deleted file, then asserts the dispatcher proceeds by relaunching for the second grouped slot (no `set -e` abort).
- **Source**: user

## Decision 3: Caller of `reuse_slot_result`
- **Question**: How many call sites does `reuse_slot_result` have?
- **Resolution**: Exactly one call site at `scripts/dispatch-with-waterfall.sh:499` inside the phase-2 grouped loop. The fix is local; no broader caller refactor required.
- **Source**: codebase

## Decision 4: Sibling `.md` update
- **Question**: Does the change require updating the sibling contract `scripts/dispatch-with-waterfall.md`?
- **Resolution**: Yes — per `.claude/rules/script-md-siblings.md`, behavior changes must update the sibling `.md` in the same PR. The grouped-dedup section gains a sentence about reuse-failure fallback to phase-2 launch.
- **Source**: codebase

## Decision 5: Hard constraints to preserve
- **Question**: What must not break?
- **Resolution**: (a) `set -euo pipefail` remains at file top; the fix is local. (b) Happy path (source file exists) preserves exact current behavior including sidecar / ledger writes / KV emits. (c) All existing tests in `scripts/test-dispatch-with-waterfall.sh` must still pass.
- **Source**: codebase

## Decision 6: Non-goals
- **Question**: Anything explicitly out of scope?
- **Resolution**: (a) Do NOT audit other `cp` calls in the script. (b) Do NOT modify PR #2962's ledger-truncation logic. (c) Do NOT add ledger-row pruning — subsequent slots in the same group will independently fall through to relaunch (correct behavior; cost is a redundant `[[ -r ]]` probe per slot).
- **Source**: codebase
