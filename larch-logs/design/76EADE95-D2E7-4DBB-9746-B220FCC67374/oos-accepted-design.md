### OOS_1: [OUT_OF_SCOPE] Add only the file input, drop optional `--note-text`; it expands the CLI surface without helping the `/implement` guideline note path.
- **Description**: [OUT_OF_SCOPE] Add only the file input, drop optional `--note-text`; it expands the CLI surface without helping the `/implement` guideline note path.. Scenario: The wrapper already passes `--note-file`, so this extra entry point ships no extra correctness or safety value and adds another code path to test.
- **Reviewer**: Codex-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:18-22
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6409
### OOS_2: Regression harness does not pin the new append-deviation-note contract
- **Description**: Regression harness does not pin the new append-deviation-note contract. Scenario: Testing strategy runs this script but Files to modify/create does not update it; a future prompt edit could drop the helper call without a harness failure
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-architectural-guidelines-step.sh:46-58
- **Phase**: design




### OOS_3: Harness does not pin the new append-deviation-note instruction in architectural-guidelines-present.md
- **Description**: Harness does not pin the new append-deviation-note instruction in architectural-guidelines-present.md. Scenario: Present-ref regression is only covered by the new Python unit-test string grep; the shell harness invoked in the testing strategy would still pass if the helper call were removed while legacy strings remain
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-architectural-guidelines-step.sh:46-51
- **Phase**: design

### OOS_1: [OUT_OF_SCOPE] Third local copy of normalize will drift
- **Description**: [OUT_OF_SCOPE] Third local copy of normalize will drift. Scenario: `execution_issues.normalize_body_for_hash` and `run_log_batch._normalize_body_for_hash` already differ. Copying either into `architectural_guidelines.py` adds a third variant.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py
- **Phase**: design




