---
name: rebalance-test-harnesses
description: "Use when rebalancing CI test harness shards to equalise wall-clock time across the 20 shards. Fetches per-target timings from the last 5 successful CI runs on main, applies round-robin LPT repacking, creates a PR, triggers 3 verification CI runs, checks the max-min shard spread is ≤ 15 s, then reports before/after statistics (merge is left to the operator)."
allowed-tools: Bash, Read, Write
---

# /rebalance-test-harnesses

**Dev-only operator skill** (`.claude/skills/` — not exported by the plugin).

Automates the procedure documented in `docs/linting.md §Refreshing harness shard balance`
using the Python machinery in `python/harness_ci_timing.py`,
`python/harness_makefile.py`, and `python/harness_shard_packer.py`.
Keep `scripts/rebalance.md` aligned with this prompt when the script contract changes.

## Usage

```
/rebalance-test-harnesses [--repo owner/name] [--n-runs N] [--branch-prefix PREFIX]
```

All flags are optional; defaults are sensible for normal use in this repository.

## What it does (step by step)

1. Fetch `LARCH_HARNESS_TIMING` rows from the last 5 successful CI runs on `main`.
2. Compute the per-target median wall time.
3. Sort all shard targets slowest-to-fastest and distribute across 20 shards in
   round-robin order (LPT heuristic — guarantees the slowest tests never cluster).
   Before packing, run a warning-only feasibility preflight on the exact measured
   target set passed to the packer. The preflight ignores orphan timing rows
   whose targets are not present in the shard target set.
4. Write the new `test-harnesses-N:` lines to `Makefile`.
5. Validate the partition with `bash scripts/test-harness-shards-coverage.sh`.
6. Commit, push a new branch, and create a PR.
7. Wait for the first CI run (triggered automatically by the push), then trigger
   two more via `gh workflow run ci.yaml --ref <branch>`.
8. Collect timing from all three runs, compute median per-shard wall times.
9. Verify: `max_shard_total − min_shard_total ≤ 15 s`.
10. Print a before / after comparison table. BEFORE shows the estimated spread
    of the new layout from baseline medians. AFTER shows the measured spread of
    that same new layout from verification CI runs.
11. **Merge is intentionally commented out.** Inspect the PR and merge manually
    (or uncomment the `_merge_pr` call in `scripts/rebalance.py` when you are
    satisfied).

## How to invoke

Run from the repository root:

```bash
python3 .claude/skills/rebalance-test-harnesses/scripts/rebalance.py [flags]
```

Or invoke via this skill, which will call the script via Bash.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--repo` | auto-detected | `owner/name` for all `gh` calls |
| `--n-runs` | `5` | Number of baseline CI runs to sample |
| `--branch-prefix` | `rebalance-shards` | Prefix for the new git branch |
| `--n-verify-runs` | `3` | Verification CI runs to trigger after PR creation |
| `--balance-threshold` | `15` | Max acceptable shard spread (seconds) |
| `--workflow` | `ci.yaml` | Workflow file name |
| `--baseline-branch` | `main` | Branch to fetch baseline timings from |

## Python library surface

| Module | Responsibility |
|--------|---------------|
| `python/harness_ci_timing.py` | `fetch_timing_rows`, `compute_medians`, `median_shard_totals` |
| `python/harness_makefile.py` | `read_shards`, `write_shards` |
| `python/harness_shard_packer.py` | `pack` |
| `python/gh.py` | `run_log_read`, `run_list_successful`, `workflow_dispatch` (added) |

Unit tests live alongside the modules (`python/test_harness_*.py`);
run with `make py-test` or `cd python && pytest test_harness_*.py`.
