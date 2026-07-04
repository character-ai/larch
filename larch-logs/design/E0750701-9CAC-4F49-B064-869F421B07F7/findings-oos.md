### OOS_1: Step 5 external-stop recovery is undocumented for operators
- **Description**: Step 5 external-stop recovery is undocumented for operators. Scenario: Step 3 recovery is documented at docs/workflow-lifecycle.md:79. The plan adds Step 5 detach/reattach and orphan-timeout but lists no operator doc update. Operators may treat exit 143 plus absent step-5-terminal as failure instead of expected reattach.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/workflow-lifecycle.md
- **Phase**: design



### OOS_2: New test-step-5-review harness has no lint registration called out
- **Description**: New test-step-5-review harness has no lint registration called out. Scenario: Makefile wiring alone may miss agent-lint orphaned-skill-file coverage for skills/implement/scripts/test-step-5-review.sh and test-step-5-review.md.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: .claude/rules/agent-lint.toml
- **Phase**: design



### OOS_3: STALL_REASON=orphan-timeout is not named in stall branch reference
- **Description**: STALL_REASON=orphan-timeout is not named in stall branch reference. Scenario: Step 5 orphan-timeout maps to STALL_REASON=orphan-timeout in review_and_fix.py but step5-review-branches.md has no branch guidance. Debugging capped detached loops may be harder.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/references/step5-review-branches.md
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] No operator-facing Step 5 external-stop recovery doc
- **Description**: [OUT_OF_SCOPE] No operator-facing Step 5 external-stop recovery doc. Scenario: Step 3 detach/reattach is documented at `docs/workflow-lifecycle.md:79`; the plan adds the same mechanics for `/implement` Step 5 but lists no doc update, so operators may still treat a signal-stopped Step 5 as a completed review.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/workflow-lifecycle.md
- **Phase**: design



### OOS_5: [OUT_OF_SCOPE] No operator-facing Step 5 external-stop recovery doc
- **Description**: [OUT_OF_SCOPE] No operator-facing Step 5 external-stop recovery doc. Scenario: The issue and Step 8 doc update explain persist-and-resume, but the plan adds Step 5 detach/reattach/orphan behavior with no workflow-lifecycle note for operators debugging a detached implement review.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/workflow-lifecycle.md
- **Phase**: design



