# Review Round 1

- Mode: `diff`
- 6 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Design run-log docs still describe stale 21-column classification TSV
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `docs/run-logs.md` still documents the old 21-column `findings-classification.tsv` header (with `reviewer_slots`, without `body_severity`/`scope`). Run-log consumers following the doc will mis-align columns on new 23-column design TSV rows and miss `scope`/`body_severity` semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update docs/run-logs.md and docs/point-competition.md to match python/voting.py headers and weighted scoring.
  - From cursor-specialist-testing-output.txt: Replace with CLI header output, bump to 23 columns, document body_severity and scope, update lint-literal-counts width comment.
  - From codex-specialist-correctness-output.txt: Update the section from the canonical voting header and document body_severity and scope.
  - From codex-specialist-testing-output.txt: Replace the section with the canonical findings-classification header and document body_severity plus scope.


### FINDING_2: Point-competition docs still describe flat +1 accepted scoring
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `docs/point-competition.md` still documents flat +1 accepted-finding scoring and unchanged OOS math. Operators and reviewers following that doc expect flat points while live scoreboards use weighted in-scope tiering (+2/+1), contradicting `voting-protocol.md`, `python/voting.py`, and other updated docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update scoring table narrative examples pruning note and legacy no-scope fallback to match python/voting.py and the other updated docs.
  - From cursor-specialist-testing-output.txt: Update scoring table, examples, OOS flat rules, and pruning unweighted note to match voting-protocol.md.
  - From codex-specialist-correctness-output.txt: Update the scoring table and narrative for weighted in-scope scoring and flat OOS rules.
  - From codex-specialist-testing-output.txt: Update the scoring table and examples for +2 high-severity accepted in-scope findings, YES-voter severity, flat OOS, and legacy fallback.


### FINDING_3: Classification TSV parser omits neutral OOS rows from round aggregates
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-scoring-integrity-output.txt
- **Severity**: important
- **Concern**: `_parse_classification_tsv` skips neutral OOS rows (`scope=oos` or legacy OOS id) while `_parse_tally_md` still routes neutral OOS into `oos_rejected`. When `_round_counts` prefers classification TSV over `voting-tally.md`, `oos_proposed` and related Review Phase Detail OOS totals under-count neutral OOS observations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align OOS neutral handling across both parsers.
  - From codex-specialist-correctness-output.txt: Count non-accepted OOS rows in the OOS non-accepted bucket, or add OOS-neutral and include it in proposed.
  - From cursor-specialist-edge-cases-output.txt: Count neutral OOS in oos_proposed without incrementing oos_rejected; add a regression fixture for scope=oos voting_result=neutral.
  - From codex-specialist-edge-cases-output.txt: Count every non-accepted OOS result in the fallback OOS bucket, or add and propagate an explicit OOS-neutral bucket.
  - From codex-specialist-testing-output.txt: Count every non-accepted OOS TSV row toward the existing OOS proposed aggregate, or add an OOS-neutral aggregate.
  - From dyn-scoring-integrity-output.txt: Treat neutral OOS explicitly the same way tally/scoreboard do (increment a neutral OOS bucket, or map neutral OOS into `oos_rejected` for meta parity until a dedicated `OOS_NEUTRAL_COUNT` exists).


### FINDING_4: Top reviewers classification path lacks comma-split fallback when tokenization returns empty
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-scoring-integrity-output.txt, dyn-attribution-scope-output.txt
- **Severity**: important
- **Concern**: `_accepted_reviewers_from_classification` drops accepted in-scope rows when `split_classification_attribution(..., column="finding_reviewers")` returns an empty list, with no comma-split fallback. `plan_review_tally._render` already falls back to comma-split stripped segments. Label-aware tokenization failures (incomplete prune map, typos, missing human labels) can credit **0** Top reviewers points while the inline scoreboard still awards weighted points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the same comma-split fallback used in plan_review_tally._render.
  - From dyn-scoring-integrity-output.txt: Mirror the tally fallback: when `finding_reviewers` tokenization returns `[]` but the cell is non-empty, fall back to comma-split stripped segments (and optionally the pre-change behavior for single-token cells).
  - From dyn-attribution-scope-output.txt: Mirror the tally fallback in `_accepted_reviewers_from_classification`: if `reviewers` is empty after `split_classification_attribution`, fall back to comma-split segments (and optionally log a warn-only execution-issues entry). Keep the `reviewer_slots` pipe-split path unchanged.


### FINDING_5: Plan-required weighted scoreboard tests missing from review_tally
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_review_tally.py` lacks plan-required weighted scoreboard integration tests. Regressions restoring flat accepted-count scoring, missing +2 major/blocker weighting, flat OOS +1, scope=oos drift handling, or co-proposer weighted attribution in `review_tally` inline scoreboards would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add assertions for +2 major/blocker, flat OOS +1, scope=oos drift, and co-proposer attribution.
  - From cursor-specialist-testing-output.txt: Add fixtures asserting Score +2 for major/blocker in-scope, flat +1 for OOS with high severity, and comma co-proposer weighted attribution.


### FINDING_8: Whitespace-separated co-reviewer cells collapse into one synthetic reviewer
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-attribution-scope-output.txt
- **Severity**: important
- **Concern**: Whitespace-separated co-reviewer cells (e.g. `Cursor-Pragmatic Codex-Arch`) can be treated as one combined reviewer label across `voting.tokenize_finding_reviewers`, `progress_report._human_attribution_labels`, and `plan_review_tally._attribution_labels`. An accepted major finding may award +2 to one combined row instead of +2 to each known reviewer, under-crediting co-proposers in Top reviewers relative to intended competition semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Do not add combined whitespace cells as labels, or make tokenization prefer decomposition into known labels; add no-label-map regressions.
  - From cursor-specialist-edge-cases-output.txt: Do not add multi-label whitespace segments as labels; build labels from authoritative maps/manifests and split observed cells into known tokens before fallback.
  - From codex-specialist-testing-output.txt: Do not add whole whitespace-containing segments as labels, or make tokenization prefer multiple label matches; add whitespace co-proposer tests.
  - From dyn-attribution-scope-output.txt: Reuse the same sources as `plan_review_tally._attribution_labels()` (prune label map, slot tools, manifest slots, proposer map), and when mining TSV cells run `voting.tokenize_finding_reviewers` iteratively as the label set grows instead of the hyphen-only heuristic.
  - From dyn-attribution-scope-output.txt: After comma-splitting block/proposer-map segments, also union tokens from `voting.tokenize_finding_reviewers(segment, labels_so_far)` as labels accumulate, matching the shared helper semantics used at read time.


