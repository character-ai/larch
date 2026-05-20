### FINDING_4: [OUT_OF_SCOPE] The same unvalidated `ISSUE_NUMBER` was already interpolated into the PR body as `Closes #$(read_state ISSUE_NUMBER)` in `scripts/ship-pr.sh` (around lines 915–916) and passed to `tracking-issue-write.sh --issue "$issue"` in `rename_done_best_effort` (around lines 1067–1077); this change widens where that value appears (title and `PR_TITLE`) but does not introduce the trust boundary itself.
- **Reviewer**: dyn-issue-num-injection-output.txt
- **Concern**: - The same unvalidated `ISSUE_NUMBER` was already interpolated into the PR body as `Closes #$(read_state ISSUE_NUMBER)` in `scripts/ship-pr.sh` (around lines 915–916) and passed to `tracking-issue-write.sh --issue "$issue"` in `rename_done_best_effort` (around lines 1067–1077); this change widens where that value appears (title and `PR_TITLE`) but does not introduce the trust boundary itself.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] `state_set` still writes arbitrary string values into the state file via `awk -v v="$value"` (`scripts/ship-pr.sh:526-540`), including newlines in values such as `PR_TITLE`; that predates this diff and is unchanged by it.
- **Reviewer**: dyn-issue-num-injection-output.txt
- **Concern**: - `state_set` still writes arbitrary string values into the state file via `awk -v v="$value"` (`scripts/ship-pr.sh:526-540`), including newlines in values such as `PR_TITLE`; that predates this diff and is unchanged by it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh:946-948
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] git log filtered by grep -v still has pipefail/grep-empty edge cases when no subject survives the filter. All subjects match the flush skip pattern so grep exits 1; behavior depends on pipefail and assignment rules as before this change. Only worth addressing if tightening ship-pr error handling globally; unchanged by this diff aside from tail vs head.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] risk-integration: scripts/test-ship-pr.sh:151-152
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] create-pr stub always prints PR_TITLE=Title Misleading when reading stub output vs state file None required for this PR
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

