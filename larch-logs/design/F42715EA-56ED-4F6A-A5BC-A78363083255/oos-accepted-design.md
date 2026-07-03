### OOS_1: [OUT_OF_SCOPE] Audit step leaves other neither-tier runtime refs untracked by the new dropped-file ratchet
- **Description**: [OUT_OF_SCOPE] Audit step leaves other neither-tier runtime refs untracked by the new dropped-file ratchet. Scenario: sentinel-host-table.md, step2b-drafter-failsafe.md, and dialectic-clarifier.md are absent from baseline.files and baseline.conditional_files today. They use Load/load or only for (not only for background), so the new regex will not classify them. The dropped-file check only guards files already in the baseline union, so they can still regrow unseen after this PR. Issue asks for an audit; plan MAY_UPDATE handles findings case by case. Acceptable minimum-change for this PR; track separate classifier follow-ups if audit confirms runtime closure edges.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:56,301,549
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6179
