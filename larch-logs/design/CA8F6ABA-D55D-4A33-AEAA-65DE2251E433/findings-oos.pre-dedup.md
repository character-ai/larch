### OOS_1:
- **Description**: No stale-lock recovery for result-env lock helper. Scenario: Plan uses mkdir lock without EXIT trap or age-based reclaim. A crash while holding ${RESULT_ENV}.lock.d blocks later publish-tail writes when no prior PUBLISH_OK=true is visible, until manual lock cleanup.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-publish.sh:347-392
- **Phase**: design

### OOS_2:
- **Description**: SKILL driver contract still says file-first parsing for exit 1. Scenario: Step 5c will force stdout authority for exit 1 and 4, but SKILL.md still documents file-first parsing for exit 1. Prompt-side orchestrators that re-read .design-publish-result.env directly could diverge from the wrapper.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:859
- **Phase**: design

