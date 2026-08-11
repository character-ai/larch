# `rebalance-tests run` contract

## Purpose

`larch rebalance-tests run` refreshes CI shard assignments for harness lanes,
Python unit-test lanes, or both. It is the Rust workflow owner for baseline
timing collection, pure planning, candidate artifact writes, branch and pull
request publication, and post-PR verification.

Invoke it through the verified bootstrap:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" rebalance-tests run [flags]
```

## CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--kind` | `all` | Selected leg: `harness`, `python`, or `all`. |
| `--repo` | origin remote | GitHub repository in `owner/name` form; must match `origin`. |
| `--n-runs` | `5` | Successful baseline CI runs to sample, from 1 through 20. |
| `--branch-prefix` | `rebalance-shards` | Prefix for the generated branch. |
| `--n-verify-runs` | `3` | Successful verification workflow runs to dispatch. |
| `--n-python-shards` | observed | Expected `python-tests` matrix shard count. |
| `--balance-threshold` | `15.0` | Maximum Python timing spread in seconds. |
| `--max-shard-wall-clock` | `300.0` | Maximum harness CI job wall-clock in seconds. |
| `--experimental-wall-clock-override NOTE` | unset | Documented harness-regression experiment. It cannot bypass incomplete evidence. |
| `--compile-affinity TARGET=GROUP:SECONDS` | unset | Repeatable shared compile setup declaration. |
| `--workflow` | `ci.yaml` | Workflow file for baseline and verification runs. |
| `--baseline-branch` | `main` | Branch used for baseline timing data. |
| `--dry-run` | false | Plan without writing, branching, pushing, creating a PR, or dispatching CI. |

## Preflight and planning

The command fetches `origin/main`, then requires a clean, unstashed symbolic
`main` checkout whose `HEAD`, local `main`, and `origin/main` revisions match.
It repeats that check immediately before a candidate write. It reads the
selected artifact state, fetches exact successful CI cohorts through the typed
GitHub Actions service, and supplies those reports to
`larch rebalance-tests plan`.

The pure planner rejects stale, skipped, incomplete, or incompatible evidence.
The harness leg also rejects target inventory drift and a modeled or observed
wall-clock regression. The Python leg rejects empty data, incomplete coverage,
or a spread over `--balance-threshold`. An unchanged harness layout is not a
success if its measured baseline exceeds `--max-shard-wall-clock`.

The command exits before branch creation for a no-op. `--dry-run` stops after
the same preflight and planning checks.

## Writes and recovery

For a changing plan, the command validates the harness partition and atomically
writes the selected `Makefile` and `python/shard-assignments.json` artifacts.
It then creates a timestamped branch, commits only those artifacts, pushes it,
returns to `main`, and creates one non-draft pull request through the typed
GitHub service.

Before a PR exists, a failed publication restores written artifacts, returns to
`main`, and removes the local branch. If a push completed or has an ambiguous
outcome, the command reports the remote branch rather than deleting a ref it
cannot prove it owns. After a PR exists, a verification failure keeps the PR
and branch available for investigation.

## Verification

The command dispatches `--n-verify-runs` workflows on the PR branch. It waits
for each successful run, collects timing only for those exact run IDs, and sends
the reports to `larch rebalance-tests verify`. Harness verification checks the
approved slowest-shard threshold and summed runner cost. Python verification
checks expected shard coverage and spread. A documented experimental override
can acknowledge only a harness regression. It never admits missing or stale
evidence.

Merge remains operator-owned.

## Pure decision contract

`larch rebalance-tests plan` and `larch rebalance-tests verify` read one
schema-v1 UTF-8 JSON request from standard input or `--input PATH` and write
one compact JSON result followed by a newline. They have no repository,
filesystem, Git, GitHub, branch, or workflow side effects. Their nested timing
reports use the schema-v2 contract emitted by `larch ci-timing`.

## Edit in sync

Keep this file aligned with `.claude/skills/rebalance-tests/SKILL.md`,
`crates/larch-cli/src/rebalance_tests_workflow.rs`,
`crates/larch-cli/src/rebalance_tests.rs`,
`crates/larch-core/src/rebalance_tests.rs`,
`crates/larch-cli/src/ci_timing.rs`, `crates/larch-cli/src/test_shards.rs`, and
the focused workflow tests whenever the command contract changes.
