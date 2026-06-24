## Proposed Design Outline

### Goals
- Remove unconditional `MANDATORY — READ ENTIRE FILE` loads that fire when their trigger condition is absent.
- Downgrade always-needed, small reference loads from all-caps `MANDATORY` wording to plain `Read`.
- Make the `(if not already loaded at Step X)` hedges consistent across all SKILL.md call sites.

### Non-goals
- Change actual reference content or behavior.
- Alter which references are loaded on the active paths — only when/how the directive fires.
- Touch CI harnesses, Python code, or scripts.

### Approach sketch
- In `skills/design/references/settle-rc-dispatch.md`: remove the readability-style.md force-read (rc branching, no prose).
- In `skills/design/references/design-outline.md`: downgrade the readability-style.md MANDATORY (always needed but wording is heavy).
- In `skills/design/SKILL.md`: gate Step 5b.5 readability-style.md on `DIAGRAM_REQUIRED=true`; downgrade 10+ always-needed directives to plain `Read`.
- In `skills/implement/SKILL.md`: move execution-issues-tracking.md MANDATORY from section header to individual call sites; gate summary-comment-template.md load on Q/A actually occurring.
- In `skills/implement/references/phantom-probe.md`: downgrade `When to load` — no full-reference read needed when `PHANTOM_STATUS=clean`.

### Surfaces in scope
- `skills/design/SKILL.md`
- `skills/design/references/settle-rc-dispatch.md`
- `skills/design/references/design-outline.md`
- `skills/implement/SKILL.md`
- `skills/implement/references/phantom-probe.md`

### Open questions
- None.
