# Review Round 2

- Mode: `diff`
- 3 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Legacy no-scope TSV docs claim weighted scoring but code uses flat +1
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-scoring-integrity-output.txt
- **Severity**: important
- **Concern**: `docs/point-competition.md` line 20 documents legacy classification TSVs (no `scope` column) as using severity-weighted scoring, but `accepted_points_from_classification_row` in `python/voting.py` returns flat `+1` for every accepted row when `scope` is absent. Operators or downstream consumers following the doc will over-score pre-scope committed logs (expecting +2 per high-severity accepted finding; code and run-logs contract give +1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-generic-output.txt: Change line 20 to document flat `+1` for legacy no-`scope` TSVs, and change line 85 to say pruning remains unweighted accepted-minus-rejected count math.
  - From dyn-scoring-integrity-output.txt: Change line 20 to state that legacy no-`scope` TSVs score accepted rows flat `+1` (no severity weighting), with `OOS_*` ids excluded from in-scope Top reviewers via prefix fallback, matching `voting-protocol.md` and the helper.


### FINDING_2: Pruning section documents weighted net score but code uses unweighted counts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-scoring-integrity-output.txt
- **Severity**: important
- **Concern**: `docs/point-competition.md` line 85 documents conditional-spawning net score as weighted accepted points minus rejected findings, but `review_pipeline.reviewer_prune_filter` records and gates on unweighted accepted/rejected counts only. A reviewer with one accepted major (+2 on scoreboard) and one rejection has prune net 0 and avoids the net-score prune gate despite doc implying weighted net ≤ 0. Pruning net score must remain unweighted accepted-minus-rejected; weighted scoring applies to competition scoreboards and Top reviewers only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-generic-output.txt: Change line 20 to document flat `+1` for legacy no-`scope` TSVs, and change line 85 to say pruning remains unweighted accepted-minus-rejected count math.
  - From dyn-scoring-integrity-output.txt: Replace the weighted clause with unweighted language only (e.g., "Net score is unweighted accepted-minus-rejected counts"), and keep the explicit note that competition scoreboards/Top reviewers use weighted points separately.


### FINDING_6: Zero-voter degraded classification test does not assert scope column values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required effective==0 degraded classification rows must carry correct `scope` column values, but `test_findings_classification_zero_voters_tsv_rejected_rows` never asserts scope or canonical row width. A regression that drops scope or mis-tags OOS rows on the 0-judge path would pass CI while emitting malformed `findings-classification.tsv` for run-log consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


