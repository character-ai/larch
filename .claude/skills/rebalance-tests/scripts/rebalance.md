# rebalance.py contract

## Purpose

`rebalance.py` refreshes CI shard assignments for test harness lanes, Python
unit-test lanes, or both. It samples recent baseline CI timings, runs selected
pre-write gates in memory, writes selected artifacts, opens one PR, runs shared
verification CI, and reports before and after shard totals.

Harness verification is warning-only. Python verification fails closed on empty
or incomplete timing data or spread above the configured threshold.

## Primary callers

- The dev-only `.claude/skills/rebalance-tests/SKILL.md` prompt.
- Operators running the script directly from the repository root.

## CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--kind` | `all` | Selected leg: `harness`, `python`, or `all`. |
| `--repo` | auto-detected | `owner/name` for GitHub CLI calls. |
| `--n-runs` | `5` | Number of baseline CI runs to sample, from 1 through 20. |
| `--branch-prefix` | `rebalance-shards` | Prefix for the generated branch name. |
| `--n-verify-runs` | `3` | Number of verification CI runs to trigger. |
| `--n-python-shards` | `4` | Expected `python-tests` matrix shard count. |
| `--balance-threshold` | `15.0` | Maximum acceptable timing-spread threshold in seconds. |
| `--max-shard-wall-clock` | `60.0` | Harness real per-shard CI job wall-clock budget. |
| `--workflow` | `ci.yaml` | Workflow file used for baseline and verification runs. |
| `--baseline-branch` | `main` | Branch used for baseline timing data. |

## Pre-write gate

### Harness leg

When `--kind harness` or `--kind all` is selected, the script fetches baseline
`LARCH_HARNESS_TIMING` data through `larch ci-timing harness`. The Rust command
uses the typed Actions adapter, parses workflow archives, computes medians and
shard totals, and identifies untimed targets. The script validates the exact
schema-v1 field order before running the `untimed_targets` hard gate. Empty
harness rows or any untimed target abort non-zero before any write. The
selected workload is packed in memory only:

```python
measured = _select_packed_workload(medians, all_shard_targets)
new_shards = _pack_shards(measured, n_shards, guard=_GUARD)
_check_feasibility(new_shards, medians, balance_threshold)
```

The feasibility check is warning-only. It runs on packed shard totals after
`_select_packed_workload` and Rust `larch test-shard pack`, not on raw medians
alone. Reading and writing the `test-harnesses-N:` lines likewise enter the
verified bootstrap through `larch test-shard read-makefile` and
`larch test-shard write-makefile`.

### Python leg

When `--kind python` or `--kind all` is selected, the script fetches recent
successful `ci.yaml` timing through `larch ci-timing pytest` and validates its
exact schema-v1 field order. Rust parses `python-tests` `call` rows, dedupes
retried shard attempts, computes nodeid and shard medians, and reports the
observed shard count. The script aborts on zero rows, conflicting or mismatched
shard counts, or empty medians. Nodeids are LPT-packed into shard ids `1..n` in
memory only.

### Artifact cleanliness

After all selected packing succeeds and before no-op detection or any write,
the script calls `git.status_porcelain_paths` for each selected output path:
`Makefile` for harness and `python/shard-assignments.json` for Python. Dirty
paths abort with a named error. No branch or PR is created.

## Write ordering

No branch or PR is created until pre-write gates, artifact cleanliness, no-op
checks, and all selected in-memory packings succeed. For `--kind all`, the
script writes `Makefile`, validates the partition, then writes
`python/shard-assignments.json`. The assignments writer serializes to
`python/shard-assignments.json.<pid>.tmp`, then `os.replace`s it into place.
Failed serialization or I/O deletes the temp file without modifying the target.

Partition failure reverts `Makefile` only. Assignment-write failure after
partition validation reverts every path written this run via
`_revert_written_paths` and leaves the prior assignments bytes unchanged.
Rollback calls `restore_staged` before `checkout_paths` per written path after
`git.add`, commit-hook failure, or post-validate write failure. Post-commit push
failure restores the original branch before artifact rollback.

## Post-PR verification dispatch

After PR creation, every selected kind uses one shared `n_verify_runs`
`workflow_dispatch` loop on the PR branch before any leg-specific verification
collection. Harness real-wall-clock and sum-spread reports remain warning-only.
Python verification collects `python-tests` rows after dispatch completes and
fails closed on zero rows, missing shard coverage, or spread over
`--balance-threshold`. Under `--kind all`, only Python verification can force a
non-zero exit.

## Edit in sync

Keep this file aligned with `.claude/skills/rebalance-tests/SKILL.md`,
`crates/larch-core/src/ci_timing.rs`, `crates/larch-cli/src/ci_timing.rs`,
`crates/larch-core/src/test_shards.rs`, `crates/larch-cli/src/test_shards.rs`,
`python/pytest_sharding.py`, `python/conftest.py`,
`python/tests/test_rebalance_script.py`, and
`python/tests/test_pytest_sharding.py` whenever `rebalance.py` behavior, flags,
or output contracts change.
