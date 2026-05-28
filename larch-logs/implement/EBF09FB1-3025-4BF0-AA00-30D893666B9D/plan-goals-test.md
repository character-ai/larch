## Goal
Implement issue #3059: [IMPLEMENTING] [OOS] dispatch-with-waterfall.sh: phase-2 relaunches not counted in fallback cost metering\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

### Files to modify/create

#### UPDATED: `scripts/dispatch-with-waterfall.sh`

- Declare `phase2_relaunch_count=0` **before** the grouped phase-2 loop, immediately above the existing `phase2_grouped_failed=()` initializer. Placing it there guarantees the variable is bound before the fall-through path inside the loop can increment it, so a reuse-copy failure cannot trip `set -u`.
- In the `reuse_slot_result` fall-through path (the grouped-phase-2 block whose comment reads `# Stale or otherwise unreadable reuse outputs fall through to the standard phase-2 relaunch path below.`), increment `phase2_relaunch_count` after the `fi` that closes the `if reuse_slot_result …; then continue; fi` and immediately before the `launch_slot "$idx" phase2 "$alt" "$out"` call. A successful reuse takes the `continue` and never reaches the increment.
- Leave `fallback_count=0` at its current site above the phase-3 loop — it is a top-level binding (not in a subshell or function), so it remains visible at the post-phase-3 threshold check.
- Compute `combined_fallback=$((fallback_count + phase2_relaunch_count))` once, after the phase-3 collect, and use that value for both the threshold check (replace the `(( fallback_count > threshold ))` test) and the `FALLBACK_COUNTER_FILE` persisted increment (replace the `$((prior + fallback_count))` expression). The threshold variable name and default (`LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD`, default `3`) stay unchanged.
- Emit a new KV `PHASE2_RELAUNCH_COUNT` next to the existing `FALLBACK_COUNT` emit. Keep `FALLBACK_COUNT` emitting the phase-3 Claude count only — the historic semantic is preserved, the combined sum is the threshold input.

#### UPDATED: `scripts/test-dispatch-with-waterfall.sh`

- Add one new scenario modeled on the existing `slots-dedup-cp-fail.ndjson` block (the only test that already drives `reuse_slot_result` failure via `CP_STUB_FAIL_COUNTER` + `CP_STUB_FAIL_TARGET_CONTAINS`). The new scenario sets `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD=0` so a single fall-through relaunch trips the warning, then asserts:
  - `PHASE2_RELAUNCH_COUNT=1`
  - `FALLBACK_COUNT=0` (no phase-3 Claude work)
  - `WARN=cost-fallback-exceeded-threshold`
  - `DISPATCH_OK=true` (the relaunch itself succeeds — the warning is informational)
- Extend the existing `slots-dedup-cp-fail.ndjson` block with one extra assertion: `assert_line "PHASE2_RELAUNCH_COUNT=1" "$out"`. Default threshold (`3`) keeps that scenario warning-free, so no `WARN=` assertion shifts.
- Use `assert_line` for the new KV checks to match the file's existing helper.

#### UPDATED: `scripts/dispatch-with-waterfall.md`

- Append `PHASE2_RELAUNCH_COUNT` to the `Stdout keys` bullet list right after `FALLBACK_COUNT`.
- Update the `WARN=cost-fallback-exceeded-threshold` bullet so it reads: emits when **the combined phase-2 fall-through + phase-3 Claude count** exceeds `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` (default `3`). Keep the threshold default and env-var name byte-stable.
- Add one short paragraph under the existing fall-through bullet (the one beginning `If the phase-2 reuse copy fails for any cp failure mode`) noting that these relaunches now feed `PHASE2_RELAUNCH_COUNT` and the cost-threshold warning. No new headings; keep the doc compact.

#### UPDATED: `skills/review/scripts/dispatch-panel.md`

- Update the WARN sentence that currently describes `WARN=cost-fallback-exceeded-threshold` as based only on the Phase 3 fallback count, so it states the threshold uses the combined phase-2 fall-through relaunch count plus the phase-3 Claude count. Keep the existing `DISPATCH_OK` Phase-3-failure wording unchanged. No other edits to that file.

### Approach

- One file owns the behavior change (`dispatch-with-waterfall.sh`); the other three are mechanical: a regression test and two sibling-doc syncs (`dispatch-with-waterfall.md` and the `dispatch-panel.md` that consumes the same WARN contract). No new flags, no new env vars, no schema changes for downstream consumers.
- Scope is narrow by construction: the increment lives inside one `if … then continue; fi` block. Normal phase-2 alt-tool swaps (the ungrouped path that runs `launch_slot … phase2 "$alt"` from the `phase2_queue` loop) stay unmeasured, matching the Round 1 resolution.
- The threshold check operates on `combined_fallback` rather than separating into two warnings. One warning, two visible counters. Consumers grepping for `WARN=cost-fallback-exceeded-threshold` keep working unchanged; consumers parsing `FALLBACK_COUNT` keep its historic meaning.
- The `FALLBACK_COUNTER_FILE` persisted total also moves to the combined sum so cross-run aggregation matches the per-run threshold logic. Callers that pass `--fallback-counter-file` will see slightly larger persisted totals only when `reuse_slot_result` actually fell through; on the common path (no fall-through) the persisted value is unchanged.

### Edge cases

- **Multiple slots in the same group fall through.** The grouped-phase-2 loop iterates each slot in the group; each individual `reuse_slot_result` failure bumps the counter once. Two fall-throughs ⇒ `PHASE2_RELAUNCH_COUNT=2`.
- **Reuse succeeds for some slots, fails for others.** Successful reuses skip the increment (the `continue` after `reuse_slot_result` runs before the counter line). Only the failed ones count.
- **No grouped slots in the run.** Counter stays at `0`; `PHASE2_RELAUNCH_COUNT=0` is emitted unconditionally; combined sum equals `fallback_count`; behavior matches today.
- **Threshold env var is unset or non-numeric.** The existing `case "$threshold" in ''|*[!0-9]*) threshold=3 ;; esac` already normalizes; combined-sum check uses the same normalized value. No new validation needed.
- **`FALLBACK_COUNTER_FILE` unset.** The existing `if [[ -n "$FALLBACK_COUNTER_FILE" ]]` guard already short-circuits; combined sum is only referenced inside that branch and in the threshold check.

### Failure modes

- **Threshold semantic change surprises operators.** Consumers who tuned `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` based on phase-3-only counts will now see the warning fire slightly more often (when fall-through relaunches occur). Earliest signal: increased `WARN=cost-fallback-exceeded-threshold` lines in run logs. Mitigation: documented in the updated `dispatch-with-waterfall.md` and `dispatch-panel.md` bullets; default threshold (`3`) is high enough that real-world fall-through cases stay under it.
- **Counter increment lands outside the fall-through block.** If the increment is placed before the `if reuse_slot_result …` check, a successful reuse would also count, contradicting Round 1. Earliest signal: the new test scenario fails — `PHASE2_RELAUNCH_COUNT=0` expected after a successful reuse, but the assertion sees `1`. Mitigation: the test extension for the existing `slots-dedup-cp-fail` block asserts exactly `1` (the cp-stub fails one of the slots, two reuses succeed), so misplacement surfaces immediately.
- **`phase2_relaunch_count` is read before initialization.** If the declaration stays after the grouped phase-2 loop, a fall-through path under `set -u` aborts with `unbound variable` before any KV is emitted. Earliest signal: the new test scenario exits non-zero with a bash error. Mitigation: the declaration runs before the grouped phase-2 loop, immediately above `phase2_grouped_failed=()`, so the variable is bound at every increment site.

### Testing strategy

- Run `bash scripts/test-dispatch-with-waterfall.sh` after the edit. The harness must continue to pass all existing scenarios and the new one.
- Run `bash scripts/relevant-checks.sh` to exercise pre-commit hooks across the repo.
- No manual UI verification needed — `dispatch-with-waterfall.sh` is a non-interactive script with stdout-KV contract.

## Acceptance

- `scripts/dispatch-with-waterfall.sh` emits `PHASE2_RELAUNCH_COUNT=<int>` on stdout next to `FALLBACK_COUNT=<int>` on every run.
- When `reuse_slot_result` falls through to a phase-2 relaunch, `PHASE2_RELAUNCH_COUNT` is incremented by exactly one per relaunch.
- When `FALLBACK_COUNT + PHASE2_RELAUNCH_COUNT > LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` (default `3`), `WARN=cost-fallback-exceeded-threshold` is emitted.
- `FALLBACK_COUNT` keeps its existing meaning (phase-3 Claude fallback count only).
- `FALLBACK_COUNTER_FILE`, when supplied, persists the combined sum `(fallback_count + phase2_relaunch_count)`.
- `scripts/test-dispatch-with-waterfall.sh` passes with the new fall-through scenario asserting `PHASE2_RELAUNCH_COUNT=1`, `FALLBACK_COUNT=0`, `WARN=cost-fallback-exceeded-threshold`, and `DISPATCH_OK=true` under `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD=0`.
- The existing `slots-dedup-cp-fail` scenario passes unchanged plus a new `assert_line "PHASE2_RELAUNCH_COUNT=1" "$out"` assertion.
- `scripts/dispatch-with-waterfall.md` lists `PHASE2_RELAUNCH_COUNT` under Stdout keys and the WARN bullet reads `combined phase-2 fall-through + phase-3 Claude count`.
- `skills/review/scripts/dispatch-panel.md` WARN sentence reads the same combined-sum semantic.
- `bash scripts/relevant-checks.sh` passes.

diff_lines: 65

## Test plan
(no test plan section in plan-file)
