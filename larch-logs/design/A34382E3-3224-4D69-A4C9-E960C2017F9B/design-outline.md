## Proposed Design Outline

### Goals
- Cut token count in `skills/implement/SKILL.md`'s densest prose: the ~line-127 `CHECKPOINT_NEXT` paragraph, the ~254-256 `BOOTSTRAP_NEXT` dispatch rows, and Step 8+ routing prose.
- Zero behavior change: KV grammar, fenced commands, the NEVER list, and every structural/lint pin stay verbatim.

### Non-goals
- No control-flow changes. No relocating content to new reference files. No logic moved to Python.
- No edits to sibling files under `skills/implement/references/` or other skills.

### Approach sketch
- Read the file in full; tighten wording in the 3 named blocks plus any other comparably dense, low-risk prose (Context calls out "densest sections" generally).
- Before finalizing, enumerate every test/lint that pins literal strings in this file (fence-shape, structure, anti-polling-rule, quick-mode-docs-sync, consecutive-bash), since the prior pass (#5787) broke several pinned phrases and needed a follow-up fix.
- Edit sentence-by-sentence: cut redundant words, keep KV tokens, bash fences, and NEVER-list items byte-stable.

### Surfaces in scope
- `skills/implement/SKILL.md` (single file)

### Open questions
- None.
