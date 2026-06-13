### OOS_1:
- **Description**: Duplicated emit_final_summary_marked_from_disk helper in two wrappers instead of one shared sourced fragment. Scenario: Two copies can drift on empty-file guards or marker line format, causing cancellation vs publish-tail paths to behave differently
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step5c.sh:38-46,skills/design/scripts/design-step-final-summary.sh:59-66
- **Phase**: design

