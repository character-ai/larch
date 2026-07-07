### OOS_1: /release still lacks default-branch CI gating
- **Description**: /release still lacks default-branch CI gating. Scenario: The 2026-07-06 incident included release PR #6491 merging onto red `main` with green PR checks only. This plan gates `/implement` but leaves `/release` on PR-check scope.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: .claude/skills/release/SKILL.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Post-merge autonomous emergency PR ship could ship in a later phase
- **Description**: [OUT_OF_SCOPE] Post-merge autonomous emergency PR ship could ship in a later phase. Scenario: Core incident is pre-merge merge onto red `main` plus flaky retry exit; a full repair-branch open/ship state machine is a large second surface beyond blocking silent merge.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md;skills/implement/references/postmerge-emergency-repair.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] `/release` lacks the same default-branch CI gate
- **Description**: [OUT_OF_SCOPE] `/release` lacks the same default-branch CI gate. Scenario: Release PR #6491 merged on red `main` via the same PR-checks-only gate; parity would help but is outside the `/implement` issue scope.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: .claude/skills/release/SKILL.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] `/release` lacks the same default-branch CI gate
- **Description**: [OUT_OF_SCOPE] `/release` lacks the same default-branch CI gate. Scenario: Release PR #6491 merged on red main via the same PR-only gate; issue open question. Not required to fix `/implement` merge behavior.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: .claude/skills/release/SKILL.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_5: [OUT_OF_SCOPE] Empty `FAILED_RUN_ID` still falls back to `pr checks`
- **Description**: [OUT_OF_SCOPE] Empty `FAILED_RUN_ID` still falls back to `pr checks`. Scenario: Step 1b routes empty run ID to `python/cli.py pr checks`, which assumes PR context and cannot recover default-branch push failures if handoff omits `FAILED_RUN_ID`.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md:12-13
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_6: /release still has no default-branch CI health gate
- **Description**: /release still has no default-branch CI health gate. Scenario: Prior-round OOS; release PR #6491 merged on red main via the same PR-check-only gate. Same class of outage, but issue scope is `/implement` and open questions mark `/release` as follow-up.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: .claude/skills/release/SKILL.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

