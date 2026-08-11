---
# larch-run-lifecycle: shared-v1 skill=rebalance-tests
name: rebalance-tests
description: "Use when rebalancing CI test harness shards, Python unit-test shards, or both from recent timings. Creates one PR and verifies the selected shard plan."
allowed-tools: Bash, Read, Write
---

**MANDATORY: Follow the complete shared lifecycle contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `rebalance-tests`.**

# /rebalance-tests

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

**Dev-only operator skill** (`.claude/skills/` and not exported by the plugin).

Run the checked Rust `rebalance-tests run` workflow. Keep
`scripts/rebalance.md` aligned with this prompt and the command contract.

## Usage

```
/rebalance-tests [--kind {harness,python,all}] [--repo owner/name] [--n-runs N] [--branch-prefix PREFIX] [--n-verify-runs N] [--n-python-shards N] [--balance-threshold SECONDS] [--max-shard-wall-clock SECONDS] [--experimental-wall-clock-override NOTE] [--compile-affinity TARGET=GROUP:SECONDS] [--workflow FILE] [--baseline-branch BRANCH] [--dry-run]
```

All flags are optional. `--kind` defaults to `all`, and `--branch-prefix`
defaults to `rebalance-shards`.

## Safety contract

Before collecting timings, and again immediately before a candidate write, the
command fetches `origin/main` and requires a clean, unstashed symbolic `main`
checkout whose `HEAD`, local `main`, and `origin/main` revisions match. It then
uses the typed GitHub Actions owner to collect complete baseline evidence and
passes it to the pure Rust planning contract.

- `harness` preserves the complete same-run harness, bootstrap, and jobs cohort.
  It rejects missing evidence, target inventory drift, modeled wall-clock
  regressions, and an over-budget unchanged layout.
- `python` rejects empty or incomplete pytest evidence and a spread above
  `--balance-threshold`.
- `all` requires both selected legs to pass before a write.
- `--dry-run` performs the preflight and planning checks, but writes no
  artifact and creates no branch, commit, push, pull request, or workflow run.

The command exits before branch creation when the plan is a no-op. A documented
`--experimental-wall-clock-override NOTE` can admit only a modeled or measured
harness regression. It cannot bypass stale, skipped, or incomplete evidence.

## Writes, publication, and verification

The workflow writes only `Makefile` and
`python/shard-assignments.json`, through the existing shard grammar and atomic
write owners. It validates the proposed harness partition before publication.
If publication fails before a pull request exists, it restores written
artifacts, returns to `main`, and removes the local branch. A branch whose push
completed or has an ambiguous outcome is reported if the typed Git owner cannot
prove that it is safe to delete.

After it creates a pull request, the command dispatches and waits for
`--n-verify-runs` successful workflow runs on the PR branch. It verifies the
same fail-closed Rust decision contract against those exact run IDs. A failed
post-PR verification leaves the PR available for review. Merge stays
operator-owned.

## How to invoke

Run from the repository root:

```bash
cargo build --locked --release --package larch-cli
LARCH_BINARY="$PWD/target/release/larch" \
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" rebalance-tests run [flags]
```

Pass all skill arguments to `rebalance-tests run` unchanged:

```
/rebalance-tests --kind all --n-runs 3
/rebalance-tests --kind python --repo owner/name --dry-run
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--kind` | `all` | Selected leg: `harness`, `python`, or `all` |
| `--repo` | origin remote | GitHub repository in `owner/name` form; must match `origin` |
| `--n-runs` | `5` | Successful baseline runs to sample, from 1 through 20 |
| `--branch-prefix` | `rebalance-shards` | Prefix for the new branch |
| `--n-verify-runs` | `3` | Successful verification runs to dispatch |
| `--n-python-shards` | observed | Expected `python-tests` shard count |
| `--balance-threshold` | `15` | Maximum Python timing spread in seconds |
| `--max-shard-wall-clock` | `300` | Maximum harness job wall-clock in seconds |
| `--experimental-wall-clock-override NOTE` | unset | Documented harness-regression experiment |
| `--compile-affinity TARGET=GROUP:SECONDS` | unset | Repeatable shared compile setup declaration |
| `--workflow` | `ci.yaml` | Workflow file to sample and dispatch |
| `--baseline-branch` | `main` | Baseline branch |
| `--dry-run` | false | Plan without any mutation |

## Implementation surface

| Surface | Responsibility |
|--------|---------------|
| `larch rebalance-tests run` | Immutable-main preflight, planning composition, atomic writes, branch and PR publication, verification, and recovery |
| `larch rebalance-tests plan` / `verify` | Pure versioned planning and verification decisions |
| `larch ci-timing` | Typed GitHub Actions timing collection |
| `larch test-shard` | Deterministic packing and Makefile shard grammar |
| `python/pytest_sharding.py` | Runtime assignment-map loading and pytest selection |

The focused workflow tests live in
`crates/larch-cli/src/rebalance_tests_workflow.rs` and
`crates/larch-cli/tests/rebalance_tests_workflow.rs`.
