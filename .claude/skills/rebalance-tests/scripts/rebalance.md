# rebalance.py contract

## Purpose

`rebalance.py` refreshes CI shard assignments for test harness lanes, Python
unit-test lanes, or both. It samples recent baseline CI timings, runs selected
pre-write gates in memory, writes selected artifacts, opens one PR, runs shared
verification CI, and reports before and after shard totals.

Harness verification is authoritative: it fails closed on incomplete timing
evidence, a slowest-shard threshold violation, or increased summed harness
runner time. Python verification also fails closed on empty or incomplete timing
data or spread above the configured threshold.

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
| `--n-python-shards` | auto-detected | Expected `python-tests` matrix shard count. |
| `--balance-threshold` | `15.0` | Maximum acceptable timing-spread threshold in seconds. |
| `--max-shard-wall-clock` | `300.0` | Enforced harness real per-shard CI job wall-clock budget. |
| `--experimental-wall-clock-override NOTE` | unset | Documented experiment that may continue after a predicted or measured wall-clock regression; it cannot bypass missing or incompatible evidence. |
| `--compile-affinity TARGET=GROUP:SECONDS` | unset | Repeat for known shared-compile targets; `SECONDS` is additional one-time setup beyond marked child time and may be zero for co-location only. |
| `--workflow` | `ci.yaml` | Workflow file used for baseline and verification runs. |
| `--baseline-branch` | `main` | Branch used for baseline timing data. |

## Pre-write gate

### Harness leg

When `--kind harness` or `--kind all` is selected, the script fetches baseline
`LARCH_HARNESS_TIMING` and `LARCH_HARNESS_BOOTSTRAP` data through `larch
ci-timing harness`, then jobs-API wall-clock rows for the exact
`sampled_run_ids` cohort. The Rust command uses the typed Actions adapter,
preserves raw rows, computes medians and shard totals, and identifies untimed
targets. The script validates exact schema-v2 field order and rejects empty or
skipped runs, missing or unknown bootstrap rows, incompatible target-mark
counts, shard-coverage differences, and target inventory drift before any
write.

For each sampled job, fixed startup is the jobs-API wall-clock less all child
and bootstrap rows. Each target keeps its aggregate child median plus a warm
bootstrap for every marker it emits; cold-minus-warm bootstrap time is charged
once to every nonempty shard. The Rust packer receives that fixed startup and
any explicit `--compile-affinity TARGET=GROUP:SECONDS` contracts, preserving
named compile-affinity groups and charging their extra setup once rather than
duplicating it on fresh runners. The post-cleanup inventory currently has no
Cargo-backed targets, so it needs no affinity declaration; a future reviewed
exception must declare one before rebalance. The planner compares active-runner counts and keeps matrix
cells empty when a new cold setup would raise summed runner cost. A proposal is
rejected unless its predicted slowest shard is no worse than both the current model and
`min(--max-shard-wall-clock, baseline observed slowest)`.

Reading and writing the `test-harnesses-N:` lines enter the verified bootstrap
through `larch test-shard read-makefile` and `larch test-shard write-makefile`.

### Python leg

When `--kind python` or `--kind all` is selected, the script fetches recent
successful `ci.yaml` timing through `larch ci-timing pytest` and validates its
exact schema-v2 field order. Rust parses `python-tests` `call` rows, dedupes
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
collection. Harness verification requires a complete same-run jobs and
bootstrap cohort, prints predicted and observed per-shard tables, and fails if
the measured slowest shard exceeds either configured or approved wall-clock
thresholds or if median summed harness-runner time exceeds the input-layout
baseline. Python verification collects `python-tests` rows after dispatch
completes and fails closed on zero rows, missing shard coverage, or spread over
`--balance-threshold`. Under `--kind all`, either leg can force a non-zero exit.
An unchanged harness layout also exits non-zero when its exact baseline jobs-API
cohort exceeds `--max-shard-wall-clock`.

`--experimental-wall-clock-override NOTE` permits only a documented experiment
to continue after a predicted or measured wall-clock regression. It never
permits a missing, stale, skipped, or incompatible timing cohort.

## Pure Rust decision contract

`larch rebalance-tests plan` and `larch rebalance-tests verify` now expose the
pure decision core for a later orchestration cutover. They read one UTF-8 JSON
request from standard input (or `--input PATH`) and write one compact JSON
result followed by a newline. They do not inspect or mutate shard artifacts,
start processes, contact GitHub, create branches, or dispatch workflows.

Both request objects use `schema_version: 1`, `kind` (`plan` or `verify`),
`selection` (`harness`, `python`, or `all`), `options`, `harness`, and `python`.
Unselected legs are `null`; every object rejects unknown or duplicate keys.
Nested `ci-timing` inputs use the schema-v2 reports emitted by `larch
ci-timing harness`, `pytest`, and `jobs`; the shared report types and decision
core validate them. Planning supplies the expected baseline run IDs, current
harness shards or Python assignments, and matching timing reports. Verification
supplies the expected verification run IDs, proposed shard inventory or Python
shard count, the plan's harness baseline thresholds, and matching post-run
reports.

`plan` returns `change`, `noop`, `rejected`, or `overridden`. `verify` returns
`passed`, `rejected`, or `overridden`. A rejected, otherwise-valid decision
still writes its machine result and exits nonzero. Malformed, stale, skipped, or
incomplete evidence writes no result and exits nonzero. The experimental note
can change only a harness modeled or measured regression from rejected to
overridden; it cannot admit missing evidence or a Python spread failure.

The current Python driver remains the workflow owner for now. It is intentionally
not switched to these commands by this leaf; the later cutover must preserve its
artifact, branch, and verification orchestration atomically.

## Edit in sync

Keep this file aligned with `.claude/skills/rebalance-tests/SKILL.md`,
`crates/larch-core/src/ci_timing.rs`, `crates/larch-cli/src/ci_timing.rs`,
`crates/larch-core/src/test_shards.rs`, `crates/larch-cli/src/test_shards.rs`,
`python/pytest_sharding.py`, `python/conftest.py`,
`python/tests/test_rebalance_script.py`, and
`python/tests/test_pytest_sharding.py` whenever `rebalance.py` behavior, flags,
or output contracts change.
