---
# larch-run-lifecycle: shared-v1 skill=rebalance-tests
name: rebalance-tests
description: "Use when rebalancing CI test harness shards, Python unit test shards, or both from recent timings. Creates one PR and verifies the selected shard plan."
allowed-tools: Bash, Read, Write
---

**MANDATORY: Follow the complete shared lifecycle contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `rebalance-tests`.**

# /rebalance-tests

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

**Dev-only operator skill** (`.claude/skills/` — not exported by the plugin).

Automates the procedure documented in `docs/linting.md §Refreshing harness shard balance`
using the Rust `ci-timing harness`, `ci-timing pytest`, and `ci-timing jobs`
commands plus the Rust `test-shard` pack and Makefile verbs. Keep
`scripts/rebalance.md` aligned with this prompt when the script contract
changes.

## Usage

```
/rebalance-tests [--kind {harness,python,all}] [--repo owner/name] [--n-runs N] [--branch-prefix PREFIX] [--n-python-shards N] [--max-shard-wall-clock SECONDS] [--experimental-wall-clock-override NOTE] [--compile-affinity TARGET=GROUP:SECONDS]
```

All flags are optional. The default kind is `all`. The default branch prefix is
`rebalance-shards`.

## Kinds

- `harness`: Rebalances the `test-harnesses-N` shard lists in the `Makefile` by
  packing a startup- and affinity-aware cost model, then enforces real
  per-shard CI job wall-clock (jobs API) against `--max-shard-wall-clock`
  (default 300s) and the input layout's observed slowest shard. The model
  includes fixed job startup, each target's measured work, the cold-versus-warm
  timer setup cost, and any explicitly declared compile-affinity group.
- `python`: Rebalances pytest nodeid assignments from `--durations=0` timing
  rows into `python/shard-assignments.json`. Verification fails closed on zero
  parseable rows, incomplete shard coverage, or spread over threshold.
- `all`: Rebalances both artifacts in one PR. Either harness or Python
  verification can return non-zero.

## Safety gates

Before any write, branch, commit, push, or PR:

1. Selected harness work fetches schema-v2 `LARCH_HARNESS_TIMING`,
   `LARCH_HARNESS_BOOTSTRAP`, and jobs-API rows for one exact successful-run
   cohort. It rejects skipped runs, missing or unknown bootstrap rows,
   incompatible target-mark counts, shard-coverage differences, and inventory
   drift before deriving the model. Fixed startup is the residual of each real
   job wall-clock after its child and bootstrap rows; target work retains its
   measured median plus each warm bootstrap; cold-minus-warm setup is charged
   once to every nonempty shard. `--compile-affinity TARGET=GROUP:SECONDS`
   declares a known shared compile context; its extra setup is charged once,
   and zero preserves co-location without inventing a second measured cost.
   `larch test-shard pack` keeps named affinity groups together. The planner compares active
   runner counts and retains empty matrix cells when opening them would raise
   summed runner cost. A predicted slowest shard may not exceed either the
   current model or the approved wall-clock threshold.
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
leg-specific verification timing. Harness verification fails closed when the
exact verification cohort is incomplete or incompatible, when the measured
slowest shard exceeds `--max-shard-wall-clock` or the approved input-layout
threshold, or when median summed harness-runner time regresses. Python
verification fails closed on empty data, missing shard ids, or spread above
`--balance-threshold`.

An unchanged harness layout also exits non-zero when its exact baseline jobs-API
cohort exceeds `--max-shard-wall-clock`; an ordinary no-op is not an exemption.

`--experimental-wall-clock-override NOTE` is the sole exception for a
documented experiment. It can acknowledge a predicted or measured wall-clock
regression, but never bypasses missing, stale, or incompatible timing evidence.

Merge stays operator-owned.

## How to invoke

Run from the repository root:

```bash
cargo build --locked --release --package larch-cli
LARCH_BINARY="$PWD/target/release/larch" \
python3 .claude/skills/rebalance-tests/scripts/rebalance.py [flags]
```

The script enters every Rust command through `scripts/larch.sh`, so the local
checkout requires the explicit release-matched `LARCH_BINARY`.

Or invoke via this skill and pass flags directly to the script:

```
/rebalance-tests --kind all --n-runs 3
/rebalance-tests --kind python --repo owner/name
```

Forward all args from the skill invocation to the script unchanged.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--kind` | `all` | Selected leg: `harness`, `python`, or `all` |
| `--repo` | auto-detected | `owner/name` for all `gh` calls |
| `--n-runs` | `5` | Number of baseline CI runs to sample, from 1 through 20 |
| `--branch-prefix` | `rebalance-shards` | Prefix for the new git branch |
| `--n-verify-runs` | `3` | Verification CI runs to trigger after PR creation |
| `--n-python-shards` | auto-detected | Expected `python-tests` matrix shard count; inferred from CI when omitted |
| `--balance-threshold` | `15` | Max acceptable sum-estimate shard spread in seconds |
| `--max-shard-wall-clock` | `300` | Enforced real harness shard CI job wall-clock budget in seconds |
| `--experimental-wall-clock-override NOTE` | unset | Documented one-off experiment that may continue after a predicted or measured wall-clock regression; evidence failures still stop the run |
| `--compile-affinity TARGET=GROUP:SECONDS` | unset | Repeat for known shared-compile targets; `SECONDS` is extra one-time setup beyond marked child time (zero is allowed) |
| `--workflow` | `ci.yaml` | Workflow file name |
| `--baseline-branch` | `main` | Branch to fetch baseline timings from |

## Implementation surface

| Surface | Responsibility |
|--------|---------------|
| `larch ci-timing harness` | Typed successful-run log fetch, raw harness and bootstrap rows, schema-v2 cohort identifiers, medians, shard totals, and untimed-target detection |
| `larch ci-timing pytest` | Typed successful-run log fetch, pytest parsing, retry dedup, medians, and shard totals |
| `larch ci-timing jobs` | Typed Actions jobs fetch and real wall-clock medians |
| `larch test-shard pack` | Deterministic LPT packing with fixed-startup and explicit named-affinity setup costs for harness targets, plus temporary Python nodeid assignment data |
| `larch test-shard read-makefile` / `write-makefile` | Literal single-line `test-harnesses-N:` grammar parsing and atomic emission |
| `python/pytest_sharding.py` | Assignment-map loading and pytest collection selection |
| `python/larch/git/gh.py` | Verification workflow dispatch while that workflow remains Python-owned |

Rust timing fixtures and wire-contract tests live in
`crates/larch-core/src/ci_timing.rs`. Python consumer tests live in
`python/tests/test_rebalance_script.py`.

`scripts/pyrightconfig.json` sets `extraPaths` so IDEs resolve the `python/`
imports in `scripts/rebalance.py` without following the runtime `sys.path`
insert.
