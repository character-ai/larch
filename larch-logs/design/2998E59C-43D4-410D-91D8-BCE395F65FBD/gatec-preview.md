## Final Design Plan

## Plan

## Approach

- Treat the post-Pieces 2–4 tree as authoritative.
- Keep pytest behavioral authorities in `make py-test`; Bash CI shards run direct Bash-harness leaves only.
- Retain five shards unless complete `python/harness_ci_timing.py` evidence shows a material, non-local imbalance.
- Record parity, inventory, timing, and cumulative line-count evidence in implementation and PR validation notes. Do not add behavioral cases.

## Files to modify/create

### UPDATED: Makefile

- Split each migrated public target—`test-write-final-report`, `test-step-7a`, `test-oos-disposition-gate`, and `test-flush-execution-issues`—into pytest and direct delegation-smoke leaves, with the public target as the local developer aggregate.
- Keep `write-final-report-bash-harness` and any equivalent non-`test-*` `*-bash-harness` leaves as valid direct Bash leaves; do not require renaming them solely for shard discovery.
- Make each smoke leaf a direct Bash-only recipe, optionally wrapped by the existing timing marker, and assign every such leaf to exactly one `test-harnesses-N` target.
- Keep public aggregates, pytest leaves, and recipe-less targets out of shard prerequisite lists.
- Update `.PHONY` declarations and shard comments so every shard-bound direct Bash leaf, including non-`test-*` leaves, is phony and documented.
- Preserve the five-shard rollup and existing membership unless complete timing data supports a rebalance.

### UPDATED: scripts/test-harness-shards-coverage.sh

- Replace the test-prefix-only inventory with a unified direct-Bash-leaf inventory:
  - include recipe-bearing `test-*` targets whose complete recipe is Bash-harness work and contains no pytest invocation;
  - include recipe-bearing non-`test-*` Bash leaves, including `*-bash-harness` targets;
  - exclude recipe-less aggregates, direct pytest recipes, and any mixed recipe containing pytest.
- Parse target recipes and prerequisite relationships sufficiently to reject a shard member that is an aggregate, an unknown target, a direct pytest target, or an indirect path to pytest; shard members must be direct inventory leaves, apart from the coverage guard.
- Drive missing, orphan, duplicate, and `.PHONY` checks from the unified inventory so non-`test-*` Bash leaves are neither falsely orphaned nor exempt from validation.
- Preserve test-target naming validation for `test-*` recipes without imposing that naming rule on valid non-`test-*` Bash leaves.
- Preserve checks for duplicate membership, rollup completeness, shard-rule declaration and single-line form, guard placement, and shard-count-agnostic discovery.
- Extend `--self-test` fixtures to prove:
  - a non-`test-*` Bash leaf such as `write-final-report-bash-harness` is accepted when listed once in a shard and present in `.PHONY`;
  - an unsharded non-`test-*` Bash leaf is reported missing;
  - a non-leaf or unknown non-`test-*` prerequisite is rejected as an orphan;
  - a recipe-less aggregate combining pytest and Bash prerequisites is rejected when placed in a shard;
  - a direct or multi-command recipe containing pytest is excluded and rejected if scheduled by a shard.

### UPDATED: scripts/residual-bash-paths.txt

- Compare the manifest with the final tracked tree and permitted residual-Bash categories.
- Remove stale or retired entries left by Pieces 2–4.
- Retain all four thin delegation smokes, all genuine Bash harnesses, and still-permitted runtime Bash, hooks, linters, and thin wrappers.
- Keep the manifest sorted and free of missing, duplicate, symlink, or non-regular paths.

### UPDATED: agent-lint.toml

- Remove exclusions and comments for retired behavioral harnesses or obsolete fixture copying.
- Retain only narrowly justified exemptions for the four surviving delegation smokes and live sibling contracts.
- Name the pytest behavioral authorities and direct Bash smoke targets accurately.

### UPDATED: ARCHITECTURAL_INVARIANTS.md

- Update I-Outcome-1 so Step 7a behavioral backing cites `python/tests/implement/test_step_7a.py`.
- Remove `skills/implement/scripts/test-step-7a.sh` as invariant-level behavioral evidence; retain it only as delegation-smoke coverage.

### UPDATED: docs/linting.md

- Reconcile the harness inventory with the final Makefile partition and unified direct-Bash-leaf definition.
- State that shards contain only direct Bash leaves, including valid non-`test-*` `*-bash-harness` leaves; public aggregates may run pytest plus a smoke locally but must not appear in a shard.
- Distinguish pytest behavioral authority from delegation-smoke coverage for all four migrated families.
- Remove stale shard-number and inventory-count claims; point drift-prone facts to the Makefile and `make test-harness-shards-coverage`.
- Correct five-shard CI and branch-protection guidance to match the current aggregate gate and workflow.
- Document the measured timing decision and retain five shards when a rebalance is not justified.

### MAY_UPDATE: .github/workflows/ci.yaml

- Parse recent successful-run data with `python/harness_ci_timing.py` before changing the matrix.
- Change shard list, displayed total, or comments only when complete measured totals show material imbalance that cannot be corrected within the existing five shards.
- Keep `test-harnesses-gate`, Makefile shard definitions, and any workflow matrix in lockstep.
- Do not change CI merely because pytest and aggregates are excluded from the Bash-leaf inventory.

## Edge cases

- A recipe-less aggregate can hide pytest and Bash prerequisites; it is never a shard leaf.
- A multi-command recipe containing any pytest invocation is not a Bash leaf.
- A non-`test-*` direct Bash leaf counts once and must be phony and assigned exactly once.
- A multi-invocation Bash harness counts once while preserving every timing row.
- Historical timing rows using retired aggregate labels do not establish timing for new smoke leaves.
- Manifest and reference cleanup use the final merged tree, not the original issue inventory.
- The guard remains valid if a measured future change adds or removes a numeric shard.

## Failure modes

- Indirect pytest scheduling duplicates the `python-tests` CI dependency.
- A test-prefix-only inventory falsely reports valid `*-bash-harness` leaves as orphaned.
- A non-leaf aggregate in a shard bypasses direct-harness partitioning.
- Removing a smoke from the manifest excludes it from shell lint coverage.
- Partial or retried timing logs produce an unsound rebalance.
- Workflow and Makefile shard definitions diverge.

## Testing strategy

- Run `make test-harness-shards-coverage`.
- Run `bash scripts/test-harness-shards-coverage.sh --self-test`.
- Inspect the resolved Make dependency graph: every direct Bash leaf appears in exactly one shard; no shard member is an aggregate or reaches pytest.
- Run `python3 python/cli.py residual-bash paths`, the residual-Bash lint path, and `make lint-bash32`.
- Run `make lint-retired-scripts`.
- Run the four public developer aggregates and confirm both pytest and delegation-smoke lanes pass.
- Run `make py-test` and `make test-harnesses`.
- Parse recent successful CI logs with `python/harness_ci_timing.py`; record shard totals and the keep-or-rebalance decision.
- Audit Pieces 2–4 migrated-case parity against pytest authorities.
- Compute cumulative `git diff --numstat` from the partition-series base through Piece 5, excluding committed run logs; confirm net deletion remains near 6,500–7,500 lines and explain variance.

difficulty: MODERATE
oversize_override: operator
diff_lines: 300
