### OOS_1:
- **Description**: Plan duplicates starting-round and findings-path validation inline instead of reusing `validate_step3_loop_starting_round` / `step3_loop_validate_tmpdir_file` from the loop driver. Scenario: Future edits to loop validation rules may not be mirrored in the wrapper, causing divergent accept/reject behavior
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3-review.sh:57-69
- **Phase**: design

### OOS_2:
- **Description**: Plan duplicates starting-round and findings-path validation inline instead of reusing `validate_step3_loop_starting_round` and `step3_loop_validate_tmpdir_file` from the loop driver. Scenario: Future loop validation changes may not be mirrored in the wrapper, causing divergent accept/reject behavior
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3-review.sh:57-69
- **Phase**: design

### OOS_1:
- **Description**: Script contract docs for new flags are not listed for update. Scenario: `design-step3-review.md` and `design-step3-state.md` get ownership notes but entry/postplan `.md` contracts stay stale after `--reentry` and completion-only flags land
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step3-entry.md,skills/design/scripts/design-step2b-postplan.md
- **Phase**: design

