## Proposed Design Outline

### Goals
- Reduce `approval-gates.md` token count by ~15% via in-place prose-density pass.
- Collapse repeated "See full plan" re-fire prose to a single normative statement with terse back-references.
- Preserve all structural test pins, contract literals, KV grammar, option labels, and question text verbatim.

### Non-goals
- No control-flow, gate-semantics, or behavior changes.
- No edits to SKILL.md, test harnesses, Python, or any other file.
- No removal of load-bearing compaction-resilience duplication (NEVER / anti-halt blocks; this file has none, so N/A).

### Approach sketch
- Apply Strunk-and-White active-voice compression to all prose paragraphs (header, "When"/"Behavior" intros, loop-exit, state invariants).
- Gate A: merge "When" + "Behavior" paragraphs; remove restated "first-time entry" footnotes in Loop exit; tighten "See full plan branch (re-entry only)" to a short reference.
- Gate C: compress the very long "When" paragraph; collapse the three separate "See full plan → re-fire" prose repetitions into one canonical note; shorten Gate C "Other dispatch" sub-bullets.
- State invariants: rewrite passive constructions as active; trim redundant rewording of facts already stated above.

### Surfaces in scope
- `skills/design/references/approval-gates.md` (single file, in-place rewrite).

### Open questions
- None.
