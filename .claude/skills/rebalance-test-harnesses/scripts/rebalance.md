# rebalance.py contract

## Purpose

`rebalance.py` refreshes CI test harness shard assignments so the harness lanes have a lower wall-clock spread.
It samples recent baseline CI timings, repacks Makefile shard targets, opens a PR, runs verification CI, and reports before and after shard totals.

## Primary callers

- The dev-only `.claude/skills/rebalance-test-harnesses/SKILL.md` prompt.
- Operators running the script directly from the repository root.

## High-level behavior

1. Read the current `test-harnesses-N` targets from `Makefile`.
2. Fetch `LARCH_HARNESS_TIMING` rows from recent successful baseline CI runs.
3. Compute per-target median seconds.
4. **Hard gate:** refuse to rebalance (exit 1, loud error) if any shard target has no timing data.
5. Select the measured workload that is also present in the shard target set.
6. Pass the selected workload to `pack()` for round-robin LPT packing.
7. Run the warning-only feasibility check on the packed shard totals.
8. Write the new shard lines and validate coverage.
9. Create a branch and PR for the new Makefile layout.
10. Trigger verification CI runs and collect median per-shard totals.
11. Print BEFORE and AFTER tables for the new shard layout.

BEFORE is estimated from baseline per-target medians for the new layout.
AFTER is measured from verification CI runs for that same new layout.

## CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--repo` | auto-detected | `owner/name` for GitHub CLI calls. |
| `--n-runs` | `5` | Number of baseline CI runs to sample. |
| `--branch-prefix` | `rebalance-shards` | Prefix for the generated branch name. |
| `--n-verify-runs` | `3` | Number of verification CI runs to trigger. |
| `--balance-threshold` | `15.0` | Maximum acceptable shard spread in seconds. |
| `--workflow` | `ci.yaml` | Workflow file used for baseline and verification runs. |
| `--baseline-branch` | `main` | Branch used for baseline timing data. |

## Timing-completeness hard gate

Before packing, `untimed_targets(all_shard_targets, medians)` (from `harness_ci_timing`) lists every shard target with no timing data.
If that list is non-empty the run prints each offending target and exits 1 — it never emits a layout.
An untimed target is invisible to `pack()` (zero weight), so it silently piles onto whichever shard the packer thinks is lightest and creates an unbalanced "monster" shard the balancer never measures.
Every `test-harnesses` target must therefore emit a `LARCH_HARNESS_TIMING` row via `timing harness-mark`.
A genuinely new test blocks a rebalance until it has run in CI at least once; instrument it (or wait for one CI run), then retry.

## Feasibility preflight

The preflight checks whether the estimated packed shard spread exceeds the configured threshold.
It is warning-only.
It never aborts the rebalance.

The check runs after the hard gate and packing:

```python
measured = _select_packed_workload(medians, all_shard_targets)
new_shards = pack(measured, n_shards, guard=_GUARD)
_check_feasibility(new_shards, medians, args.balance_threshold)
```

Totals are computed from packed shard targets.
Missing timing data contributes `0.0` seconds.
This means orphan timing rows from baseline CI logs remain ignored because they are not present in the packed shard layout.
The warning names the estimated packed spread, configured threshold, heaviest shard total, and lightest shard total.

## Edit in sync

Keep this file aligned with `.claude/skills/rebalance-test-harnesses/SKILL.md` and `python/test_rebalance_script.py` whenever `rebalance.py` behavior, flags, or output contracts change.
