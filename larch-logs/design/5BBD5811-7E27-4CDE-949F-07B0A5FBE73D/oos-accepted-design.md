### OOS_2: Stall diagnostics still say guidelines warning refresh after outcome flush rename
- **Description**: Stall diagnostics still say guidelines warning refresh after outcome flush rename. Scenario: After replacing _flush_guidelines_warning_before_pr, failure stalls will still read architectural-guidelines warning run-log refresh skipped, which misleads operators debugging outcome-commit failures
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/implement/ship.py:205-247
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6411
### OOS_3: No shared tmpdir filename constant for the outcome sidecar
- **Description**: No shared tmpdir filename constant for the outcome sidecar. Scenario: Other guideline artifacts use named constants in architectural_guidelines.py; the plan only names the committed batch file, which invites path drift between writer, flush staging, and tests
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py:27-36
- **Phase**: design




### OOS_2: Stable reason tokens are unspecified
- **Description**: Stable reason tokens are unspecified. Scenario: Outcome JSON carries a `reason` field used for histograms, but the plan does not define a bounded token set or validation beyond audit presence checks. Typos will fragment drop analytics over time.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/implement/ship_guidelines.py
- **Phase**: design




