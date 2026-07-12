## Proposed Design Outline

### Goals
- Reduce the partition flow to exactly 1 AskUserQuestion by precomputing the scheme inline.
- Main agent (no subagents) computes the optimal partition before prompting.
- After filing, auto-wire block-issue relations for intra-piece deps and migrated original-issue deps.

### Non-goals
- Removing the panel-dispatch or aggregate Python infrastructure.
- Changing the issue-filing, annotate, or close-original mechanics.
- Changing plan-size threshold trigger conditions.

### Approach sketch
- Replace decompose-panel.md §2–§6 (panel dispatch + 3-stage AskUserQuestion) with an inline main-agent computation step that reads plan/feature and produces a ranked partition scheme.
- Present the precomputed scheme as option 1 in a single AskUserQuestion (alongside Override and Other).
- Remove the rc=12 first prompt from SKILL.md ("Let my panel split for you"); the combined question in decompose-panel.md replaces it.
- After §7c annotate succeeds, run dep migration: fetch original issue's blocked-by/blocking graph, re-emit each edge onto the appropriate new pieces.
- Add `decompose migrate-deps` Python verb in `decompose.py`; update tests in `test_decompose.py`.

### Surfaces in scope
- `skills/design/references/decompose-panel.md`
- `skills/design/SKILL.md` (rc=12 prompt and SKILL.md decompose-panel.md §4 reference)
- `python/larch/design/decompose.py`
- `python/tests/design/test_decompose.py`
- `python/larch/cli.py` (register `decompose migrate-deps` verb)

### Open questions
- None.
