### [rejected] FINDING_15

### FINDING_15: correctness: scripts/ship-pr.sh:1231-1235
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] semver_lt runs on new_version without the same strict semver regex used for origin. Malformed or empty NEW_VERSION can confuse the regression guard or trip brittle numeric compares under error-sensitive settings. Validate new_version with ^[0-9]+.[0-9]+.[0-9]+$ before semver_lt or skip correction when invalid.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: risk-integration: scripts/test-larch-log.sh:188-214
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale-run regression covers sibling dirs under the same staging root but not symlink REPO_ROOT vs LARCH_LOG_REPO_ROOT mismatch from the plan rationale. Less lock-in on the exact prefix-strip bug class named in the implementation plan. Optional: add a symlinked-repo variant if that edge remains load-bearing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: security: scripts/ship-pr.sh:1231-1234
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] semver_lt applied to classify NEW_VERSION without prior strict semver validation Malformed NEW_VERSION can break [[ numeric compares or error under set -e, derailing run_rebase_rebump Validate new_version with the same ^[0-9]+.[0-9]+.[0-9]+$ pattern (or skip regression logic) before semver_lt
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_5

### FINDING_5: architecture: scripts/larch-log.sh:425-428
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] rel hardcodes larch-logs layout parallel to larch_log_repo_run_dir. Future helper-only path layout change could desync commit pathspec from actual repo_path. Share one helper for the relative path or derive from normalized repo_path + REPO_ROOT.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_6

### FINDING_6: architecture: scripts/ship-pr.sh:385-395 + .claude/skills/bump-version/scripts/apply-bump.sh:42-52
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicate semver_lt implementations in the same PR. Divergent edits could yield inconsistent ordering semantics across apply-bump vs run_rebase_rebump. Extract a single shared semver comparison helper and source it from both scripts.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

