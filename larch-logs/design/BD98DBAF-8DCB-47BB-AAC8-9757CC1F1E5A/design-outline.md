## Proposed Design Outline

### Goals
- Regression-pin the research-phase contract (NOT_SUBSTANTIVE terminal behavior, FINDING_N ballot IDs, synthesis gating, STATUS-gated input exclusion) in `test-research-structure.sh`.
- Add a round-summary.env NOT_SUBSTANTIVE count assertion to `test_plan_review.py`.
- Remove dead code: ns-retry references in `collect_results.py`, stale retry-era stubs in `Makefile`/`test-prompt-template-invariants.sh`, dual voter-exclude sidecar-read path in `tally-code-votes.sh`.
- Fix `docs/linting.md` row for `test-classify-bump` to drop stale release-helper-CLI claim.

### Non-goals
- Refactoring the `/research` skill beyond adding assertions to its structure harness.
- Changing `voting.py` behavior beyond moving the voter-exclusion call-site.
- Extending `lint-harness-pytest-partition.py`'s `extract_pytest` guard (prefer Makefile fix only).
- Filing a new `/rebalance-tests` follow-up: issues #4600 and #4503 are already closed.

### Approach sketch
- Add new assertions (Checks 14+) to `scripts/test-research-structure.sh` pinning NOT_SUBSTANTIVE terminal language, FINDING_N ballot protocol, synthesis gating, and STATUS-gated exclusion.
- Add one pytest assertion in `python/test_plan_review.py` for NOT_SUBSTANTIVE count in `round-summary.env`.
- In `python/collect_results.py::resolve_collector_stderr_tail_file`, remove the two lines that check for `ns_retry_tail`.
- In `python/legacy_review_shell/tally-code-votes.sh`, remove the `parse-rate-diag-matches` sidecar-read path and call the Python live-check helper directly instead.
- In `Makefile` and `scripts/test-prompt-template-invariants.sh`, remove the stale retry-era stub targets/code.
- Update `docs/linting.md` line 222 to remove the "release helper CLIs" claim from the `test-classify-bump` row description.
- Item 6: Identify and fix the specific Makefile recipe(s) that pass multiple pytest files to a single target.
- Item 7: Document in this plan that no action is required (follow-ups already resolved).

### Surfaces in scope
- `scripts/test-research-structure.sh`
- `python/test_plan_review.py`
- `python/collect_results.py`
- `python/legacy_review_shell/tally-code-votes.sh`
- `python/voting.py` (inspect call-site for live-check consolidation)
- `Makefile` (retry-era targets; Item 6 multi-file fix)
- `scripts/test-prompt-template-invariants.sh`
- `scripts/lint-harness-pytest-partition.py` (read-only; fix goes in Makefile)
- `docs/linting.md`

### Open questions
- None.
