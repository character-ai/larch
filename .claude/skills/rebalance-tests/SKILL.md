---
name: rebalance-tests
description: "Use when rebalancing CI test harness shards, Python unit test shards, or both. Fetches recent CI timings, repacks selected shard artifacts, creates one PR, triggers verification CI, keeps harness verification warning-only, and fails closed for Python timing verification."
allowed-tools: Bash, Read, Write
---

# /rebalance-tests

**Dev-only operator skill** (`.claude/skills/` — not exported by the plugin).

Automates the procedure documented in `docs/linting.md §Refreshing harness shard balance`
using the Python machinery in `python/ci_timing_fetch.py`,
`python/harness_ci_timing.py`, `python/pytest_ci_timing.py`,
`python/harness_makefile.py`, `python/harness_shard_packer.py`, and
`python/pytest_sharding.py`. Keep `scripts/rebalance.md` aligned with this
prompt when the script contract changes.

## Usage

```
/rebalance-tests [--kind {harness,python,all}] [--repo owner/name] [--n-runs N] [--branch-prefix PREFIX] [--n-python-shards N]
```

All flags are optional. The default kind is `all`. The default branch prefix is
`rebalance-shards`.

## Kinds

- `harness`: Rebalances `Makefile` `test-harnesses-N` targets. Verification
  spread failures are warning-only and exit 0.
- `python`: Rebalances pytest nodeid assignments from `--durations=0` timing
  rows into `python/shard-assignments.json`. Verification fails closed on zero
  parseable rows, incomplete shard coverage, or spread over threshold.
- `all`: Rebalances both artifacts in one PR. Harness verification stays
  warning-only. The Python leg drives any non-zero verification exit.

## Safety gates

Before any write, branch, commit, push, or PR:

1. Selected harness work fetches baseline `LARCH_HARNESS_TIMING` rows, computes
   medians, rejects untimed shard targets, then runs `_select_packed_workload`,
   `pack`, and warning-only `_check_feasibility` in memory.
2. Selected Python work fetches baseline `python-tests` `call` rows, rejects
   zero parseable rows, dedupes latest attempts per `(run_id, shard)` before
   median computation, validates observed CI shard count against
   `--n-python-shards`, and LPT-packs nodeids in memory.
3. `--kind all` requires every selected gate to pass before the first write.
4. Every selected artifact path must be clean in git: `Makefile` for harness,
   `python/shard-assignments.json` for Python. Dirty paths abort with a named
   error and no branch or PR.

## Write and rollback order

For `--kind all`, the script writes `Makefile` first and validates the harness
partition before writing assignments. `python/shard-assignments.json` is written
atomically through a temp file plus `os.replace`. Partition failure reverts
`Makefile` only. Assignment-write failure reverts every path already written by
the run. Rollback restores staged state before checking out each written path.

## Verification

After PR creation, one shared `n_verify_runs` `workflow_dispatch` loop runs for
every selected kind. Only after those runs complete does the script collect
leg-specific verification timing. Harness spread remains informational. Python
verification fails closed on empty data, missing shard ids, or spread above
`--balance-threshold`.

Merge stays operator-owned.

## How to invoke

Run from the repository root:

```bash
python3 .claude/skills/rebalance-tests/scripts/rebalance.py [flags]
```

Or invoke via this skill and pass flags directly to the script:

```
/rebalance-tests --kind all --n-runs 3
/rebalance-tests --kind python --n-python-shards 4 --repo owner/name
```

Forward all args from the skill invocation to the script unchanged.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--kind` | `all` | Selected leg: `harness`, `python`, or `all` |
| `--repo` | auto-detected | `owner/name` for all `gh` calls |
| `--n-runs` | `5` | Number of baseline CI runs to sample |
| `--branch-prefix` | `rebalance-shards` | Prefix for the new git branch |
| `--n-verify-runs` | `3` | Verification CI runs to trigger after PR creation |
| `--n-python-shards` | `4` | Expected `python-tests` matrix shard count |
| `--balance-threshold` | `15` | Max acceptable sum-estimate shard spread in seconds |
| `--max-shard-wall-clock` | `60` | Real harness shard CI job wall-clock budget in seconds |
| `--workflow` | `ci.yaml` | Workflow file name |
| `--baseline-branch` | `main` | Branch to fetch baseline timings from |

## Python library surface

| Module | Responsibility |
|--------|---------------|
| `python/ci_timing_fetch.py` | Shared successful-run log fetch loop |
| `python/harness_ci_timing.py` | Harness timing parsing, medians, shard totals |
| `python/pytest_ci_timing.py` | Pytest duration parsing, retry dedup, medians, shard totals |
| `python/harness_makefile.py` | `read_shards`, `write_shards` |
| `python/harness_shard_packer.py` | `pack` |
| `python/pytest_sharding.py` | Assignment-map loading and pytest collection selection |
| `python/gh.py` | `run_log_read`, `run_list_successful`, `workflow_dispatch`, `job_durations` |

Unit tests live alongside the modules. Run with `make py-test` or targeted
pytest commands under `python/`.

`scripts/pyrightconfig.json` sets `extraPaths` so IDEs resolve the `python/`
imports in `scripts/rebalance.py` without following the runtime `sys.path`
insert.
