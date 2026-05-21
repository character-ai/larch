### FINDING_10: [OUT_OF_SCOPE] `manifest_field` swallows JSON errors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `manifest_field` can swallow JSON errors and exit 0, yielding empty `MANIFEST_STATUS` / `MANIFEST_PR_NUMBER`; malformed `manifest.json` could silence later-phase requirements and yield false OK for partial trees—not introduced by this diff.
- **Suggested revision**: Treat as separate hardening if desired.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_12: [OUT_OF_SCOPE] Pre-existing weak assertion pattern beyond Test 15
- **Reviewer(s)**: dyn-test-assertion-quality-output.txt
- **Concern**: Same theme as FINDING_8: Test 1 and several later tests already follow substring-only success checks with `|| true`; tightening should ideally be consistent rather than only on Test 15; input also references commits on branch since merge-base with `main`.
- **Suggested revision**: If improving harness strictness, apply exit assertions consistently and keep commit/PR scope boundaries explicit for reviewers.
```

Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] execution-issues greps lack `LC_ALL=C`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: execution-issues probes use `grep` without `LC_ALL=C`; unchanged by the new allowlist work—possible locale edge cases if pursuing repo-wide `grep` locale hygiene.
- **Suggested revision**: Track separately as optional repo-wide hygiene if desired.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] Harness-wide `|| true` plus substring-only assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-assertion-quality-output.txt
- **Concern**: Multiple tests (including Test 1 and Test 15’s broader context) already use `|| true` with substring-only checks—weaker regression signal on success vs failure is pre-existing across the harness, not introduced solely by newer tests; branch history spans hardening, run-log flush, review, and relevant-checks commits.
- **Suggested revision**: Optional follow-up—add exit-code assertions consistently across the harness if tightening signal, not only on individual new tests.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] `RUN_DIR` argv not normalized to a fixed root prefix
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `RUN_DIR` is accepted from argv without normalizing to a fixed root prefix—pre-existing; could interact oddly with `..` or symlinks for run-dir checks independent of this branch’s manifest-path work.
- **Suggested revision**: Consider `realpath` and a prefix check if hardening the CLI surface becomes a goal.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

