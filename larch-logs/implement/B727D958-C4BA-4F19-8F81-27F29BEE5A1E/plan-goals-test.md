## Goal
Implement issue #5429: [IMPLEMENTING] Prune 193 py-test-duplicated targets from test-harnesses; drop ripgrep install.

## Implementation Plan
## Problem

The `test-harnesses` CI job (20 shards) barely shrank after the Bash-to-Python (E3) migration. Root cause: the migration rewrote the bash regression harnesses into pytest files and repointed the Makefile `test-*` targets from `bash test-X.sh` to `pytest python/test_X.py`, preserving the 20-shard structure. About **72% of the job is now a second, slower copy of the `python-tests` job**.

## Evidence

- The 20 shards hold **268 distinct leaf targets**.
  - **193 (72%)** are pytest-wrappers (`pytest python/test_*.py`, some `-k` / marker-sliced), covering **64 distinct test files**.
  - **75 (28%)** are genuine bash regression harnesses (`.sh`) with no py-test equivalent: hook guards (`deny-edit-write`, `block-submodule`, `hook-bg-poll-guard`), bash linters (`lint-bash32`, `lint-bare-grep-probe`, `lint-awk-multibyte-regex`, `lint-renderer-substitution-safety`), SKILL.md / prompt-structure checks (`design-structure`, `implement-structure`, `references-headers`, `subskill-anchors`, `prompt-template-invariants`). These are the only part of the job with a unique role.
- **All 64 pytest files also run in `python-tests`**: `make py-test` is `pytest` over all of `python/`, sharded 16 ways. There is no `testpaths` / `collect_ignore` / carve-out in `python/conftest.py` or `python/pyproject.toml`, and `pytest_sharding.py` assigns every collected nodeid to a shard.
  - `python/shard-assignments.json` explicitly co-assigns **927 nodeids** from 50 of those 64 files to py-test shards; the other 14 files run there via round-robin fallback.
  - Net: roughly **1,000+ test cases execute in both the 20-shard `test-harnesses` matrix and the 16-shard `python-tests` matrix**.
- **Per-target overhead**: 196 of 197 pytest recipes wrap pytest as `cli.py timing harness-mark --label $@ -- python3 -m pytest …`. That is two Python interpreter starts plus a fresh pytest collection per target, about 193 times. py-test pays that once per shard (16 times). Same tests, far more startup cost.
- The `#4439` / `#4459` partition work (`scripts/lint-harness-pytest-partition.py`) de-duplicated these files *within* the harness shards but never addressed that the whole set is already covered by `python-tests`. The LPT packer and `LARCH_HARNESS_TIMING` rebalancer are infrastructure built around the redundancy, not a justification for it.

## Secondary finding: vestigial ripgrep install

- `.github/workflows/ci.yaml` (the `test-harnesses` job) caches and installs `rg` "required by `python/test_agents.py` static migration guards" (FINDING_11, PR #1367; cache added #2349), with a per-run "Verify ripgrep" step.
- **No current `python/test_*.py` invokes the `rg` binary.** The only live `rg` use in the tree is `python/review_pipeline.py` (runtime feature, optional via `shutil.which("rg")`, mockable in tests).
- The install / cache / verify steps appear vestigial. Confirm no test needs real `rg`, then drop them.

## Proposed change (both in this issue)

1. **Prune the 193 pytest-wrapper targets** from the `test-harnesses` Makefile shards and the CI matrix. Keep only the 75 bash regression harnesses. Coverage loss is zero, because `make py-test` already runs every pruned test.
   - Re-scope or retire the surrounding machinery: `LARCH_HARNESS_TIMING` marks, `python/harness_shard_packer.py` (LPT packer), `python/harness_ci_timing.py`, the `rebalance-tests` skill (harness half), `scripts/lint-harness-pytest-partition.py`, `test-harness-shards-coverage`.
   - Collapse the 20-shard matrix toward the handful needed for the remaining bash harnesses.
2. **Remove the ripgrep install / cache / verify steps** from the `test-harnesses` job in `.github/workflows/ci.yaml`, after confirming no test invokes the `rg` binary.

## Acceptance criteria

- `test-harnesses` shards contain only bash (`.sh`) regression-harness targets. No `pytest python/test_*.py` invocations remain in the harness shards.
- `make py-test` still collects and runs all `python/test_*.py` files. No coverage regression.
- ripgrep install / cache / verify steps removed from `ci.yaml`; CI green without them.
- Stale prose and counts updated: Makefile shard comments, `docs/linting.md`, the `rebalance-tests` skill, and any "20 shards" references.

## Caveat

A few of the 75 bash-classified targets may invoke pytest or `cli.py` internally; verify each during implementation. The headline finding (193 pytest-wrappers fully duplicated by `make py-test`) is verified directly and is unaffected by that caveat.

## Test plan
(no test plan section in plan-file)
