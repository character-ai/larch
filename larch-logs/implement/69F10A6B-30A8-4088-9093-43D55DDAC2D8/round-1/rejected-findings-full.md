### [rejected] FINDING_2

### FINDING_2: `test-implement-finalize.sh` teardown no longer models `gh issue view` failure or pins `RENAME_STATUS=ok` after prefetch removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: The former `STUB_GH_ISSUE_VIEW_FAIL` teardown path was replaced by a happy-path style check (including a composed `--round-trip` token) without a `RENAME_STATUS=ok` pin, weakening direct regression signal for the old finalize-side prefetch failure contract and overlap with branch A/B tests if `tracking-issue-write` behavior drifts. Because `rename_issue` no longer calls `gh issue view`, the block may not document or guard resiliency if a future change re-adds a pre-rename `gh` fetch in `implement-finalize.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move degraded gh view coverage to test-tracking-issue-write.sh or restore an explicit RENAME_STATUS=ok assertion for this state block; align comments with the new ownership of gh issue view.
  - From cursor-specialist-correctness-output.txt: Rename the assertion to document argv-only scope and/or add gh view failure coverage to scripts/test-tracking-issue-write.sh where gh is still invoked.

---


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

