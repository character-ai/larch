### OOS_1:
- **Description**: [OUT_OF_SCOPE] Post-force-push UNKNOWN retry has the same missing BEHIND re-check. Scenario: If post-force-push UNKNOWN resolves to BEHIND, CI is checked before branch staleness is reported, so pending CI can mask main advancement
- **Reviewer**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/merge-pr.sh:210-240
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2911
### OOS_2:
- **Description**: Retry counts are hard-coded as 4 vs 3 without named constants or documented rationale in-repo. Scenario: Future tuning requires editing two call sites and risks accidental asymmetry
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/merge-pr.sh:17-30
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2912
### OOS_3:
- **Description**: Plan adds G3 for UNKNOWN→CLEAN but no symmetric empty→CLEAN recovery case. Scenario: __EMPTY__ transient API blips that resolve on retry are untested even though the helper treats empty like UNKNOWN
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/test-merge-pr.sh:386-397
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2913
