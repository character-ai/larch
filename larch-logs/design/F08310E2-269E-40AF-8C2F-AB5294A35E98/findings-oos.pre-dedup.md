### OOS_1: MAY_UPDATE leaves Bash and new Python sanitizer paths as parallel implementations
- **Description**: MAY_UPDATE leaves Bash and new Python sanitizer paths as parallel implementations. Scenario: Behavior can drift on future sanitizer or logging tweaks unless both surfaces are edited
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3b-sanitize.sh:1-172
- **Phase**: design



### OOS_2: Sentinel host table still documents `step-5b.5` as entry/sanitize fence host
- **Description**: Sentinel host table still documents `step-5b.5` as entry/sanitize fence host. Scenario: Maintainer pause audits will misread where the sentinel is written after sanitize moves into Step 5c publish
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/sentinel-host-table.md:24
- **Phase**: design



### OOS_3: Maintainer sentinel table still lists sanitize as a separate Step 5b.5 fence
- **Description**: Maintainer sentinel table still lists sanitize as a separate Step 5b.5 fence. Scenario: After sanitize moves into Step 5c Python, the host table misstates where step-5b.5 is written. Normal orchestration does not load this file, so impact is maintainer-only drift on pause/resume audits.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/sentinel-host-table.md:24
- **Phase**: design



### OOS_4: Sentinel host table still documents sanitize as a Step 5b.5 fence
- **Description**: Sentinel host table still documents sanitize as a Step 5b.5 fence. Scenario: After the change, normal sanitize completion lives inside Step 5c publish preamble; the host table will mislead pause/resume maintainers about where step-5b.5 is written.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/sentinel-host-table.md:24
- **Phase**: design



