## Proposed Design Outline

### Goals
- Port the 6 in-scope review-pipeline bash bodies into `python/review_pipeline.py` as typed functions over `proc.Runner`; remove `run_legacy`.
- Cut every consumer to `python3 cli.py review …`, delete the retired bash + `.md` + `test-*.sh`, and keep `make lint`, `py-lint`, `py-test`, `lint-retired-scripts` green.

### Non-goals
- Do not port the out-of-scope façade bodies (`aggregate-findings`, `tally-code-votes`, `emit-tally`, `compose-review-findings`, `log-phase`); they stay bash behind their own façades.
- Do not redesign pipeline behavior or the panel model. This is a port with bounded cleanup.

### Approach sketch
- Port `review-core.sh` (orchestrator) plus `dispatch-panel`, `collect-findings`, `gather-context`, `check-reviewer-failure-threshold`, and `reviewer-prune`; absorb `lib-prune-decision.sh`.
- The ported orchestrator keeps calling the out-of-scope façades via their existing `cli.py review …` verbs.
- Cleanup is allowed; change an output contract only when every in-repo consumer (façade bash, skill `.md`, tests) is updated in the same PR.
- Add baseline pytest in `python/test_review_pipeline.py`; cut `/review` and `/design` plan-review consumers.

### Surfaces in scope
- `python/review_pipeline.py`, `python/test_review_pipeline.py`
- delete: `python/legacy_review_shell/{review-core,dispatch-panel,collect-findings,gather-context,check-reviewer-failure-threshold}.sh`, `scripts/reviewer-prune.sh`, `scripts/lib-prune-decision.sh` (+ `.md`/`test-*.sh` siblings)
- consumers: `skills/review/**`, `skills/design/**` plan-review, `python/review_and_fix.py`, `docs/**`, `python/migrated-scripts.tsv`

### Open questions
- None.
