## Decision 1: Treatment of claim #1 (Gate A/B trailer-guard wiring)
- **Question**: Claim #1 is already wired in the current repo (SKILL.md Gate A re-entry + Gate B post-apply, approval-gates.md §Shared post-apply pipeline, discussion-rounds.md all run `--snapshot-trailers`/`--dedup` before `ACTION=EMIT_PLAN`). How should the design treat it?
- **Resolution**: Treat as resolved AND add a regression guard — a structural pin in `test-design-structure.sh` asserting the Gate A/B trailer-guard anchors remain present so the gap cannot silently reopen. Do NOT re-implement the guard.
- **Source**: user (scope) + codebase (already-wired finding)

## Decision 2: Comprehensiveness of the awk unit harness (claim #2)
- **Question**: How deep should the new `lib-plan-optional-trailers.awk` unit harness be?
- **Resolution**: Comprehensive. Directly test all 4 awk modes (`keys`/`values`/`parse`/`has_key`) with edge cases: last-match-wins on duplicate trailer keys, the `0[89]` octal guard, `mechanical_churn` true/false, `diff_deleted`, empty/missing trailers, and block-boundary breaks (non-trailer line halts the block scan).
- **Source**: user

## Decision 3: Doc-sibling (.md) coverage
- **Question**: The existing trailer scripts lack sibling `.md` files (pre-existing script-md-siblings convention gap). How far should coverage go?
- **Resolution**: Backfill all — add sibling `.md` for the new harness AND for the existing `lib-plan-optional-trailers.{sh,awk}` and the four `test-trailer-*.sh`.
- **Source**: user

## Hard constraints (from codebase)
- Do NOT modify the behavior of `lib-plan-optional-trailers.awk` or `lib-plan-optional-trailers.sh`; this is a test/doc/regression-guard change only. The awk is the unit-under-test — keep it byte-stable unless a genuine bug is found (none expected).
- New/edited shell must stay Bash 3.2-compatible (BASH_AUTHORING §3); no hard lint enforces sibling `.md`, but the convention and plan-review panel expect it.
- New test scripts follow the existing pattern: thin CLI adapters invoked by the combined `test-trailer-helpers.sh` (which is already wired into Makefile target `test-trailer-helpers` and shard `test-harnesses-12`) — minimize new Makefile/shard wiring.

## Non-goals
- No changes to the runtime trailer-guard wiring itself (claim #1 already resolved).
- No backfill of unrelated missing `.md` siblings outside the trailer-script set.
