### OOS_1:
- **Description**: 10+12 slot plan-review manifest has same dual-vendor waterfall shape but no fallback_group wiring. Scenario: Duplicate Codex work on large plan-review panels after decompose-only wiring
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:1-200
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2928
### OOS_2:
- **Description**: No harness update to assert single Codex launch with fallback_group. Scenario: Regression slips for #2885 panel path
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-decompose-panel-dispatch.sh:1-999
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2929
