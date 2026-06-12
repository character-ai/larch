### OOS_1:
- **Description**: [SCOPE-REDUCTION] Plan keeps writing empty dialectic-resolutions.md and contested-decisions.md forever. Scenario: Retired dialectic machinery is gone, but every run still maintains three no-op artifacts and conflict guards for sketch/dialectic filenames
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:512-513; skills/design/scripts/design-step2a.sh:129-131
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Plan updates `design-step3-state.md` but not the `.sh` helper that still restores `.completed/step-2a.5` on Gate A direct-review re-entry.. Scenario: After dialectic removal, writing a `2a.5` completion marker is vestigial state that no active step consumes. It adds resume surface area without behavior benefit.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3-state.sh:103-105
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] Plan only retires `debate-retry` migrated-script rows, not the already-absent `read-design-classification` / `read-workflow-path` rows.. Scenario: The TSV still advertises retired bash surfaces that no longer exist, which can mislead migration audits. It does not break runtime behavior.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/migrated-scripts.tsv:119-123
- **Phase**: design

### OOS_1:
- **Description**: skills/design/scripts/design-step2a.sh:131. Scenario: [SCOPE-REDUCTION] Plan keeps writing empty dialectic-resolutions.md and contested-decisions.md after dialectic removal
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:512
- **Phase**: design

### OOS_1:
- **Description**: dialectic-protocol.md remains listed as a Cursor runtime template after the protocol file is deleted. Scenario: SECURITY.md line 301 still names skills/shared/dialectic-protocol.md alongside voting-protocol.md and validation-phase.md. This does not break CI or local rerun mappings, but security docs will point at a removed path post-merge.
- **Reviewer**: Cursor-dyn-delete-unwire-completeness
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: SECURITY.md:301
- **Phase**: design

