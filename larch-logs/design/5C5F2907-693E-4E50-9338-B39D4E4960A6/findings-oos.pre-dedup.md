### OOS_1: [OUT_OF_SCOPE] Prefetch may duplicate analyze_issues gh field fallback
- **Description**: [OUT_OF_SCOPE] Prefetch may duplicate analyze_issues gh field fallback. Scenario: python/larch/issue/analyze_issues.py already retries gh issue list when stateReason or url are unavailable. Reimplementing that degrade path in analyze_bugs adds surface area without new behavior.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Boilerplate stripping beyond larch:plan is unspecified
- **Description**: [OUT_OF_SCOPE] Boilerplate stripping beyond larch:plan is unspecified. Scenario: The binding spec mentions stripping boilerplate as well as plan blocks, but the plan only calls strip_named_block for larch:plan. Residual template text may still inflate triage prompts.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/issue/analyze_bugs.py
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Bundle prompts lack explicit untrusted delimiters
- **Description**: [OUT_OF_SCOPE] Bundle prompts lack explicit untrusted delimiters. Scenario: FINDING_9: capped bundles still embed issue bodies and diffs inline without delimiter envelopes used elsewhere (issue_wire, deps). Prompt-injection risk is reduced by caps but not documented.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: .claude/agents/bug-fix-triage.md
- **Phase**: design



