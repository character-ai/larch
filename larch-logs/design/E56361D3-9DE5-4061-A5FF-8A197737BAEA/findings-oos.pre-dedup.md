### OOS_1: Appending auto error reporting without updating the reference header triplet Contract / When to load.
- **Description**: Appending auto error reporting without updating the reference header triplet Contract / When to load.. Scenario: The new section documents teardown failure-report and stage-terminal-state semantics outside Step 5 finalization, but the header still says load only at Step 5 entry for OOS/diagram/publish work. Maintainers may skip the section when debugging early-exit Final summary paths.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/finalize-step5.md:1-8
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Frontmatter Contract/When-to-load not updated after append
- **Description**: [OUT_OF_SCOPE] Frontmatter Contract/When-to-load not updated after append. Scenario: Appending `## /design auto error reporting` without updating the column-0 `**Contract**:` / `**When to load**:` triplet leaves progressive-disclosure metadata claiming Step-5-finalization-only while the file also holds teardown-reporting prose spanning earlier failure paths.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/finalize-step5.md:1-8
- **Phase**: design



