### OOS_1: [OUT_OF_SCOPE] Self-review composes rejected-finding and OOS prose with no local readability anchor.
- **Description**: [OUT_OF_SCOPE] Self-review composes rejected-finding and OOS prose with no local readability anchor.. Scenario: The `--self-review` and `self-review-required` paths draft user-facing finding text here, but the plan wires only `execution-issues-tracking.md` and `stall-recovery.md` for /implement locals.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/references/self-review.md:18-28
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Alias generation still emits redirect-only SKILL bodies without readability directives.
- **Description**: [OUT_OF_SCOPE] Alias generation still emits redirect-only SKILL bodies without readability directives.. Scenario: Generated aliases like `skills/im/SKILL.md` only forward to `/implement`; adding a readability load there buys little because they compose almost no prose.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/core/alias_skill.py:42-58
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Firm UPDATE to `test-brainstorm-prompts.sh` adds churn without new enforcement.
- **Description**: [OUT_OF_SCOPE] Firm UPDATE to `test-brainstorm-prompts.sh` adds churn without new enforcement.. Scenario: The harness checks `<READABILITY_STYLE>` token lines and `brainstorm.md` path pins only; it never asserts a readability file path, so repointing the shared file cannot fail this test.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/design/scripts/test-brainstorm-prompts.sh:16-43
- **Phase**: design



