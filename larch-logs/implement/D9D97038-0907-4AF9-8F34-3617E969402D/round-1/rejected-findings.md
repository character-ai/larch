### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Non-step3 ledger rows should count without a trigger
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-testing
- **Severity**: important
- **Concern**: `_ledger_file_has_escalation_evidence` should return true for any parsed non-`step3-review` row even when `trigger` is missing; only `step3-review` rows should require an allowlisted trigger, and rows without `site` should stay non-evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Return true as soon as site!=step3-review; only gate trigger membership for step3-review rows, and keep malformed rows without site as non-evidence.
  - From codex-specialist-testing: Return true as soon as site is parsed and is not step3-review; only require an allowed trigger for step3-review rows, and add a regression test for a non-step3 row without trigger if supported.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

