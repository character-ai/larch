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
4. Select the measured workload that is also present in the shard target set.
5. Pass the selected workload to `pack()` for round-robin LPT packing.
6. Run the warning-only feasibility check on the packed shard totals.
7. Write the new shard lines and validate coverage.
8. Create a branch and PR for the new Makefile layout.
9. Trigger verification CI runs and collect median per-shard totals.
10. Print BEFORE and AFTER tables for the new shard layout.

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

## Feasibility preflight

The preflight checks whether the estimated packed shard spread exceeds the configured threshold.
It is warning-only.
It never aborts the rebalance.

The check runs after packing:

```python
measured = _select_packed_workload(medians, all_shard_targets)
new_shards = pack(measured, n_shards, guard=_GUARD, extras=extras)
_check_feasibility(new_shards, medians, args.balance_threshold)
```

Totals are computed from packed shard targets.
Missing timing data contributes `0.0` seconds.
This means orphan timing rows from baseline CI logs remain ignored because they are not present in the packed shard layout.
The warning names the estimated packed spread, configured threshold, heaviest shard total, and lightest shard total.

## Edit in sync

Keep this file aligned with `.claude/skills/rebalance-test-harnesses/SKILL.md` and `python/test_rebalance_script.py` whenever `rebalance.py` behavior, flags, or output contracts change.
