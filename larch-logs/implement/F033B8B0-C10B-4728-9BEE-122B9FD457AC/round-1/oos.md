### FINDING_10: [OUT_OF_SCOPE] architecture: .claude/skills/release/scripts/release-finish.md:18-19
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] mergeCommit.oid missing falls back to origin/main tip when plugin.json version matches. Running finish before mergeCommit is populated could tag main tip instead of squash merge OID. Pre-existing contract; out of Phase 4 scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_12: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-doc-narrative-consistency-output.txt
- **Concern**: - **architecture** — Across `release-finish.md`, `SKILL.md` Step 6, and `scripts/promote-release.md` Purpose/Edit-in-sync, the reframed story is aligned: `release-finish.sh` creates tag + Release (`gh release create` without `--prerelease` at `.claude/skills/release/scripts/release-finish.sh:340`), then calls `promote-release.sh` (`:349-351`); partial-failure and promote-only retry paths match; no edited file still describes per-merge `release-tag.yaml` or prerelease-by-default cuts.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_13: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-doc-narrative-consistency-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:289-297` — Pre-existing local-tag reconciliation can still fail closed if a remote tag appears between probes; removing `release-tag.yaml` race docs does not change script behavior, only drops workflow-specific recovery prose (intentional per plan).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-doc-narrative-consistency-output.txt
- **Concern**: - **architecture** `.claude/rules/gh-body-file.md` — `release-finish.sh` uses `--notes-file` but was not added to the rule’s `paths:` list (pre-existing; unrelated to this diff’s single-line removal).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_5: [OUT_OF_SCOPE] risk-integration: .claude/skills/release/scripts/release-finish.sh:289-297
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Local-tag reconciliation may exit before re-probe when remote tag appears after first ls-remote; previously discussed vs release-tag.yaml race. Concurrent tag creation (manual or second /release) between probes can still hit ERROR=local tag … not TARGET_OID on paths unchanged by this PR. Re-probe remote_tag_commit_oid before local_oid != TARGET_OID branch in a follow-up touching release-finish.sh (not required for Phase 4 doc/workflow deletion).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] risk-integration: .claude/skills/release/scripts/release-finish.sh:310-318
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Local-tag reconciliation can fail before post-push re-probe when remote_oid is stale. Primarily affected concurrent release-tag.yaml races; less likely after workflow removal. Pre-existing; fix with re-probe before local_oid branch if still desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

