### OOS_1:
- **Description**: 10+12 slot plan-review manifest has same dual-vendor waterfall shape but no fallback_group wiring. Scenario: Duplicate Codex work on large plan-review panels after decompose-only wiring
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:1-200
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_2:
- **Description**: No harness update to assert single Codex launch with fallback_group. Scenario: Regression slips for #2885 panel path
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-decompose-panel-dispatch.sh:1-999
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_3:
- **Description**: §4 parent-unset list still names only dispatch-plan-voters.sh; plan adds more parents via linter but not the canonical prose list. Scenario: Drift between docs and enforced callers
- **Reviewer**: Cursor-dyn-bash32-ledger-design
- **Severity**: latent
- **Focus area**: architecture
- **Location**: BASH_AUTHORING.md:73
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

