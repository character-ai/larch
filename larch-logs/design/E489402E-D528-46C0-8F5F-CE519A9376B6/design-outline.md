## Proposed Design Outline

### Goals
- Move the Preflight item-5 `AUDIT=refuse` clarify-flow (~12 always-loaded lines) out of `skills/implement/SKILL.md` into `skills/implement/references/preflight-plan-audit.md`.
- Collapse SKILL.md item 5 to a one-line pointer that retains the "Exit 3" statement.
- Preserve the forked-target `--repo "$UPSTREAM_REPO"` threading notes inside the relocated flow.

### Non-goals
- No runtime behavior change: clarify-state/comment/label ordering, partial-failure contract, and exit codes stay identical.
- Do not move the `/implement` orchestrator exit-codes table or the exit-3 sub-case A/B/C row; they stay inline.
- No Python port; no edits to item 4 audit logic or other Preflight items.

### Approach sketch
- Append one new section to `preflight-plan-audit.md` (after the `AUDIT=refuse` file-result section) holding the moved clarify-flow bullets, including `--repo` threading.
- Replace the SKILL.md item-5 body with a one-line pointer into that section; keep "Exit 3" and the existing exit-code table below it unchanged.
- The reference is already MANDATORY-loaded at item 4 on the only path that reaches `AUDIT=refuse`, so no new load is needed.

### Surfaces in scope
- `skills/implement/SKILL.md` — Preflight item 5.
- `skills/implement/references/preflight-plan-audit.md` — new relocated-flow section.

### Open questions
- None.
