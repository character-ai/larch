### OOS_1: correctness: docs and templates still carry U+2014 in status examples
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-lint-scope
- **Severity**: important
- **Concern**: The planned status-report templates in `skills/shared/progress-reporting.md` and `skills/research/references/citation-validation-phase.md` still use U+2014, and the markdown matcher misses some inline-backtick `⏩` template shapes such as `skills/implement/references/step18-cleanup.md:17`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-lint-scope: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_2: correctness: writer alias is over-broadly treated as a sink
- **Reviewer(s)**: dyn-dyn-lint-scope
- **Severity**: latent
- **Concern**: Seeding `breadcrumb_writer_names` with `writer` up front makes every `writer.emit(...)` call look like a `BreadcrumbWriter` sink, which can false-positive unrelated helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-lint-scope: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)
