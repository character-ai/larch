### FINDING_14: [OUT_OF_SCOPE] architecture: CHANGELOG.md:10-11
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] #3134 changelog entry is under Fixed but describes new lint and ship-pr behavior. Miscategorized release note only. Move to Added/Changed in a follow-up if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] architecture: feature_description vs plan
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Original mawk [[:space:]] narrative vs multibyte-only lint scope. Docs disagree on root cause class; code follows plan non-goals. Align issue/PR narrative in a docs-only follow-up.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] risk-integration: scripts/test-ship-pr-fix-loop-2632.inc.sh:403-467
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] 2632 include has LAUNCHER_EXIT=0 vendors without HEAD advance but is not sourced from test-ship-pr.sh. Those scenarios are not exercised in make test-ship-pr-fix-loop CI after the new HEAD check. Re-source the include or update 2632 cases with sentinel/git-commit stubs (separate follow-up).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2287-2290
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Per-job local fix success path lacks HEAD-non-advance detection added to run_ci_fix_vendor. Per-job fix can exit 0 through _stage_and_push with unchanged Fix-CI HEAD and still loop to max-retries instead of exit 3. Mirror the effective_head gate in the per-job _stage_and_push success branch (follow-up issue).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_33: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:1942-1943
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] BAIL_REASON first-fixer-non-health is set when any winning tier produces no Fix-CI commit. Operators reading state may assume Cursor-only failure when Codex/Claude no-op triggered the bail. Rename reason or split tier-specific bail keys (cosmetic; pre-existing naming).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2287-2290
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Per-job local fix calls _stage_and_push_ci_fixes without HEAD-non-advance escalation. Local fix can succeed with no Fix CI failure commit while vendor path would bail; behavior predates #3134. Track separately if per-job and vendor paths should share the same health contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/lint-awk-multibyte-regex.md:55
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Rule 2 example references dac0d00c and [[:space:]] alongside the em-dash. Readers may think the lint targets POSIX classes in dynamic regex. Clarify the example targets the em-dash byte only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

