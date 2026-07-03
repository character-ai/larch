## Proposed Design Outline

### Goals
- Cut prose density roughly 15% across the three Step 2 implementer prompts (`_implementer-base.md` plus its two generated derivatives), matching the density-pass style already used on sibling prompt families.
- Keep every schema/grammar surface byte-identical: JSON templates, jq predicates, the manifest fields table, and the generator's token substitutions and regex anchors.
- Ratchet the panel-tier prompt-closure baseline down to lock in the measured savings.

### Non-goals
- No change to the manifest JSON schema itself (`skills/implement/references/codex-manifest-schema.md` stays untouched).
- No restructuring of the codex/cursor generator architecture, heading names, or Hard-guards numbering.
- No fix for the unrelated, already-dormant item-numbering mismatch in the generator's cursor-strip regex (pre-existing, out of scope).

### Approach sketch
- Hand-tighten prose paragraphs in `agents/_implementer-base.md` (the shared source), leaving headings, numbered hard-guard prefixes, code fences, and the PLR0911-pinned sentence untouched.
- Tighten the kind-specific intro prose embedded in `_implementer_text()` inside `python/larch/rendering/_rendering_generators.py`, without touching its regex/replace logic.
- Regenerate `agents/codex-implementer.md` and `agents/cursor-implementer.md` from the updated source and generator.
- Refresh `python/skill-closure-baseline.json` so the panel-tier ratchet reflects the smaller size.

### Surfaces in scope
- `agents/_implementer-base.md`
- `agents/codex-implementer.md` (generated, not hand-edited)
- `agents/cursor-implementer.md` (generated, not hand-edited)
- `python/larch/rendering/_rendering_generators.py` (`_implementer_text` prose only)
- `python/skill-closure-baseline.json`

### Open questions
- None.
