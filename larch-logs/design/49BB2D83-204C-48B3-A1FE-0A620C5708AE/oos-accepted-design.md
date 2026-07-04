### OOS_1: [OUT_OF_SCOPE] Duplicate `--skip-approve` auto-approve print literal lives outside the three approved files
- **Description**: [OUT_OF_SCOPE] Duplicate `--skip-approve` auto-approve print literal lives outside the three approved files. Scenario: Step 1d.7 calls this the only `--skip-approve` carve-out and instructs printing `⏩ 1d.7: outline — auto-approved` before design-outline.md owns the gate; scrubbing design-outline.md:79 alone leaves that path emitting em-dash
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:249
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6303
### OOS_2: [OUT_OF_SCOPE] Step 5b warning and skip breadcrumbs are hardcoded in Python, not only in finalize-step5.md
- **Description**: [OUT_OF_SCOPE] Step 5b warning and skip breadcrumbs are hardcoded in Python, not only in finalize-step5.md. Scenario: Updating finalize-step5.md print literals (lines 49, 53, 74, 98, 105) without touching design_step5b.py leaves runtime warnings like annotate-skipped and ISSUES_FAILED still using em-dash; grep on the three markdown files can pass while operator-visible output is unchanged
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5b.py:168-269
- **Phase**: design




