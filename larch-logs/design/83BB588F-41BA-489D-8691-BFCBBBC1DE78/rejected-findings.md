### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:2445-2447
- **Concern**: `larch_quiet_append_done_trap` placement is underspecified for a trap-less script. Scenario: `ship-pr.sh` has no `trap … EXIT`; calling the helper only inside `main()` after `larch_quiet_init` is correct, but “after last trap” wording invites a wrong EOF placement
- **Proposed resolution**: State explicitly: in `main()` immediately after `larch_quiet_init` (line 2446); no prior EXIT trap to chain


### [Plan Review] FINDING_58

### FINDING_58:
- **Reviewer(s)**: Cursor-dyn-deferred-ci-gap
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lint-foreground-markers.sh:64-82
- **Concern**: New scripts/breadcrumb-monitor.md and scripts/lib-redact-streaming.md are outside the linter scan set. Scenario: list_md_files only scans skills/** and .claude/rules — sibling docs under scripts/ are never scanned for stale Foreground required phrases or missing background+monitor pair examples
- **Proposed resolution**: Note in NEW sibling .md sections that fence examples must follow the background+monitor contract; defer expanding lint-foreground-markers scan to scripts/*.md to OUT_OF_SCOPE item 9


