### OOS_1: [OUT_OF_SCOPE] skills/design/SKILL.md:249 still emits em-dash skip-approve breadcrumb
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: important
- **Concern**: When `SKIP_APPROVE_REQUESTED=true`, the Step 1d.7 auto-approve instruction in `skills/design/SKILL.md` (line 249) still prints `⏩ 1d.7: outline — auto-approved (--skip-approve)` with an em dash. The sibling reference `skills/design/references/design-outline.md` already uses the colon form (`outline: auto-approved`). The em-dash scrub is therefore incomplete outside the files already edited in scope; the live `/design` skill surface can still emit banned punctuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
