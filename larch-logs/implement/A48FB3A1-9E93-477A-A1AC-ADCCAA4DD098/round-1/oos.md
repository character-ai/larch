### FINDING_15: [OUT_OF_SCOPE] `SECURITY.md` not updated for paths-file trust surface
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `SECURITY.md` was not updated alongside the new collector trust surface; downstream security reviewers relying on `SECURITY.md` may miss `--paths-file` trust assumptions that appear only in `scripts/collect-agent-results.md`. Add a short `SECURITY.md` bullet cross-referencing the `--paths-file` trust model and any deferred allowlist note.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Aggregate branch diff noise from `larch-logs`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Multiple flushed `larch-logs` commits / large run-log hunks dominate branch-wide or precomputed `diff.txt` views versus the focused functional change (e.g. commit `9fc0773d`), lowering signal for reviewers who rely only on aggregate diffs; logs are intentional per `docs/run-logs.md`. Use path-filtered diffs, `git show 9fc0773d`, or otherwise narrow review to the contract change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: None required for #2637 correctness; use targeted git show 9fc0773d or path-filtered diff for reviews


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

