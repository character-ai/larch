## Decision 1: File scope — Bucket 1 only
- **Question**: Cover all 14 files, Bucket 1's 9 files, or a smaller subset?
- **Resolution**: Bucket 1 only. The 9 files that run the full file under multiple target names: `test_run_logs.py`, `test_implement_dispatch.py`, `test_redact.py`, `test_release.py`, `test_design_lifecycle.py`, `test_plan_review_panel.py`, `test_decompose.py`, `test_plan_scout.py`, `test_design_summary.py`. Bucket 2's 5 heavier already-sliced files are out of scope for this plan.
- **Source**: user

## Decision 2: Rebalancing — sequenced follow-up, not this PR
- **Question**: Include shard wall-time re-measure + rebalance in this plan?
- **Resolution**: Yes in intent, but sequenced. This PR does partition + retirement only. Rebalancing is a tracked follow-up: run `/rebalance-tests --kind harness` after the change lands on `main` and CI emits fresh timings for the new slices. The new selections have no CI timing until then, so a same-PR rebalance would use stale or noisy data. Acceptance must name this follow-up.
- **Source**: user

## Decision 3: Retiring duplicate targets — allowed
- **Question**: May the plan retire genuine duplicate full-file targets, or preserve every target?
- **Resolution**: Allowed. Where multiple targets run the identical full file with no semantic distinction, retire the extras down to one canonical target and update shard membership in the Makefile and `scripts/test-harness-shards-coverage.sh` (`test-harnesses-N` prereqs). Otherwise slice into disjoint `-k` / node-id selections (one `not (...)` catch-all per file).
- **Source**: user

## Constraint A: Preserve semantic env distinctions (hard)
- **Question**: Are any multi-target runs semantically distinct rather than pure duplicates?
- **Resolution**: Yes. `test_run_logs.py`'s `test-verify-run-log-completeness` runs with `env -u LARCH_VERIFY_MANIFEST`, so it is NOT a pure duplicate. Preserve that env distinction when slicing or retiring. Audit each file's targets for similar env / flag distinctions before treating any as a duplicate.
- **Source**: codebase / issue

## Constraint B: Guard + structural invariants must pass (hard)
- **Question**: What is the acceptance gate?
- **Resolution**: `make test-harness-shards-coverage` must pass. That covers (1) the strict-partition guard (`scripts/lint-harness-pytest-partition.py`): every test in each enforced file covered by exactly one target, no overlap, no uncovered; and (2) the Makefile shard-structure checks: shard membership (no missing/orphan/duplicate across `test-harnesses-N`), `.PHONY` membership, single-physical-line shard rules, aggregate prereq parity. Each Bucket-1 file is added to `ENFORCED` only after it partitions cleanly. The guard needs pytest on PATH (repo `python/.venv`).
- **Source**: codebase
