# Review Round 1

- Mode: `diff`
- 10 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Duplicated vote tally logic can desync TSV and markdown results
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Duplicated per-block vote-count loops in `tally-plan-review.sh` can drift, causing `findings-classification.tsv` and `voting-tally.md` to report different outcomes after future vote or judge-error changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_10: Parse-rate accepts vote-only lines despite retry text requiring axes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retry text requires four forensic axis tokens, but substantive parse-rate still accepts vote-only lines, allowing empty axes and `uncertain=true` without retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Tally doc references the wrong Makefile shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `tally-plan-review.md` documents `test-harnesses-1` while implementation uses `test-harnesses-9`, which can mislead contributors running coverage checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: Tally abort paths can leave stale findings-classification TSV
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After a successful tally, a later malformed-ballot run can exit without rewriting or removing `findings-classification.tsv`, allowing publish to stage stale per-round forensic data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Duplicated findings-classification TSV header can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The TSV header literal is duplicated between the tally writer and empty-artifact paths, so future schema changes could update only one path and publish inconsistent headers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Parser vote and tally vote semantics can diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `vN_vote` uses parser output while `voting_result` uses `vote_for_id`; insufficient parity coverage could let edge-case vote lines produce different forensic columns and panel outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Duplicate voter slots corrupt vote totals and forensic columns
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Repeating `--voter` for the same slot can double-count votes for `voting_result` while only the last file populates the corresponding `vN_*` columns, corrupting published forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Publish harness lacks absent or empty plan-review success coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Publish tests do not fully lock successful handling of absent or empty `plan-review/` directories, so allowlist regressions could break valid runs without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Voter-sourced TSV cell sanitization is not fully tested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Harness coverage checks `finding_reviewers` sanitization but not all `vN_*` voter-sourced columns, so tabs or newlines in judge output could break TSV alignment while CI passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: Panel-dispatch-failed path lacks header-only TSV coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Only the zero-findings empty-artifact path asserts header-only `findings-classification.tsv`; panel dispatch failure could stop writing the TSV unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


