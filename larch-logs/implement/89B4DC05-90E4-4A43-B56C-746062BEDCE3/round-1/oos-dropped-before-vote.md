### OOS_1: [OUT_OF_SCOPE] Step 2b anchor should precede plan composition
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The Step 2b readability MANDATORY load appears after the plan-composition instructions, so agents may begin plan bullets before loading `readability-style.md`, weakening composition-site enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Move the MANDATORY directive above plan-composition instructions.

### OOS_2: [OUT_OF_SCOPE] Manifest empty-row validation needs a test
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: nit
- **Concern**: New manifest validation for empty path/variant rows is untested, so invalid TSV rows could regress without a failing unit test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add a manifest row with empty path or variant and assert exit 2 with the new error message.

### OOS_3: [OUT_OF_SCOPE] Pass-through skill exemption for `larch-size`
- **Reviewer(s)**: dyn-dyn-skill-surface
- **Severity**: nit
- **Concern**: The skill states it passes CLI output through unchanged but still carries a full readability directive and manifest row, and the plan allowed an explicit exemption for pure pass-through skills.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-surface: The plan allowed an explicit exemption for pure pass-through skills; using the exemption would avoid a forced style read on every `/larch-size` invocation.

