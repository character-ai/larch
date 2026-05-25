### OOS_1:
- **Description**: [OUT_OF_SCOPE] Research docs use RESEARCH_TMPDIR breadcrumb paths, but breadcrumb-monitor path validation only allows IMPLEMENT_TMPDIR DESIGN_TMPDIR and REVIEW_TMPDIR. Scenario: Research background collector snippets fail path validation with exit 2 before monitoring starts
- **Reviewer**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:191-205 skills/research/references/validation-phase.md:185-199 scripts/breadcrumb-monitor.sh:28-53
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2833
