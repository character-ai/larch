## Goal
Implement issue #4237: [IMPLEMENTING] [BUG] (URGENT) /rebalance-test-harnesses: BEFORE table compares wrong shards; no feasibility check before triggering verification CI runs.

## Implementation Plan
## Plan

Two surgical bug fixes in `rebalance.py` plus a feasibility preflight that uses the exact packed workload. Also add the required sibling doc, update the skill prompt, and cover the new helper behavior with unit tests.

## Files to modify/create

### UPDATED: .claude/skills/rebalance-test-harnesses/scripts/rebalance.py

**Bug 1a, BEFORE table uses wrong shard layout:**
- Replace `current_shards` with `new_shards` in `_print_shard_table("BEFORE ...")`.
- After the fix, BEFORE and AFTER both describe the new shard assignments.
- BEFORE remains estimated from baseline medians.
- AFTER remains measured from verification runs.

**Bug 1b, PR body "before spread" reports old layout:**
- Replace `current_shards` with `new_shards` in the `baseline_spread` computation.
- After the fix, the PR body says "Before spread (estimated): Xs" where X is the estimated spread of the new assignments.

**Bug 2, add warning-only feasibility preflight using the same target set as `pack()`:**
- Do not compute feasibility from all `medians.values()`.
- Build or reuse the exact packed workload before the feasibility check:

```python
measured = {t: medians[t] for t in medians if t in all_shard_targets}
```

- Call `_check_feasibility(measured, n_shards, args.balance_threshold)` immediately before `pack()` uses `measured`.
- Keep `pack()` using the same `measured` dict.
- Add `_check_feasibility(measured, n_shards, balance_threshold)`.
- In `_check_feasibility`:
  - Return early when `n_shards == 0`.
  - Return early when `measured` is empty.
  - Compute `max_target_time = max(measured.values(), default=0.0)`.
  - Compute `ideal_shard = sum(measured.values()) / n_shards`.
  - If `max_target_time > ideal_shard + balance_threshold / 2`, print a warning and continue.
- Include in the warning:
  - Heaviest packed target name.
  - Heaviest packed target seconds.
  - Ideal shard time.
  - Balance threshold.
  - Threshold half.
  - Top 5 heaviest packed targets by time.
- The check is warning-only.
- The script must continue regardless.
- Orphan timing rows from baseline CI logs must not affect the feasibility warning unless their target is present in `all_shard_targets`.

### NEW: .claude/skills/rebalance-test-harnesses/scripts/rebalance.md

- Add the required sibling doc per `script-md-siblings.md`.
- Document:
  - Purpose.
  - Primary callers.
  - High-level behavior.
  - CLI flags.
  - The warning-only feasibility preflight.
  - The fact that feasibility uses the same measured target set passed to `pack()`.
  - Edit-in-sync pointer to `SKILL.md`.

### UPDATED: .claude/skills/rebalance-test-harnesses/SKILL.md

- Update step 10, "Print a before / after comparison table."
- Clarify that BEFORE shows the estimated spread of the new layout.
- Clarify that AFTER shows the measured spread of that same new layout.
- Add a note about the feasibility preflight before verification CI runs.
- State that the preflight ignores orphan timing rows for targets not present in the shard target set.

### NEW: python/test_rebalance_script.py

- Import helper functions from `rebalance.py` via `importlib.util.spec_from_file_location`.
- Test: infeasible packed workload emits a warning.
- Test: feasible packed workload emits no warning.
- Test: empty measured workload does not crash and emits no warning.
- Test: `n_shards == 0` does not crash and emits no warning.
- Test: orphan medians are excluded before feasibility, so a heavy orphan target does not trigger the warning when the packed workload is feasible.
- Capture stdout to assert warning presence or absence.
- Do not invoke `main()`.
- Do not run git or gh commands.

## Edge cases

- `n_shards == 0` must return before dividing.
- Empty `measured` must return without warning.
- Targets absent from `medians` already count as `0.0` in `_print_shard_table` through `medians.get(t, 0.0)`.
- Timing rows for removed targets may remain in baseline logs. They must not affect feasibility or the heaviest-target warning.
- The feasibility check may still warn for a real packed target that makes the configured threshold impossible.

## Failure modes

1. If only the table call is fixed, the PR body can still report old-layout spread.
2. If feasibility uses all medians, removed targets can hide or create warnings that do not match the workload passed to `pack()`.
3. If the warning aborts, operators lose the option to accept an improvement that still misses the configured threshold.
4. If the measured dict is built twice with different filters, feasibility and packing can diverge again.

## Testing strategy

- `cd python && pytest test_rebalance_script.py`
- `bash scripts/relevant-checks.sh`

## Acceptance

Plan reviewed and approved via /design panel (2 rounds, 0 accepted in-scope findings).

diff_lines: 101

## Test plan
(no test plan section in plan-file)
