## Proposed Design Outline

### Goals
- Reduce `skills/design/references/plan-review.md` by ~15% tokens in-place.
- Keep all normative contracts byte-stable: `python/cli.py` invocations, agent-lint S030 path pins, voter line format, and `FINDING_N`/`OOS_N` templates.
- Zero behavior change; all structural pins and tests still pass.

### Non-goals
- No changes to panel, voting, or dedup semantics.
- No edits to `python/plan_review.py` or any Python code.
- No changes to `SKILL.md`'s citation line (C1 scope).

### Approach sketch
- Tighten the header block (Consumer / Contract / When to load) by merging redundant sentences.
- Compress "loop-internal to `python/plan_review.py`" repetition across sections into a single short reference.
- Cut explanatory filler from prose sections while keeping the normative content.
- Preserve code fences, all `python/cli.py` / path literals, and byte-preserved templates verbatim.

### Surfaces in scope
- `skills/design/references/plan-review.md` (single file, in-place edit)

### Open questions
- None.
