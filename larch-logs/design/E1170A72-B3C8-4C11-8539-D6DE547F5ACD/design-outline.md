## Proposed Design Outline

### Goals
- Feed parsed `ARCHITECTURAL_GUIDELINES.md` entries to the plan-review panel (design Step 3) and the code-review panel (all code review: implement Step 5 + standalone `/review`).
- Let a guideline deviation become a proposable, votable, accept/reject finding through the existing machinery.
- Reuse `read_guidelines()` + `emit_untrusted_content_block(tag="architectural_guidelines", ...)`.

### Non-goals
- No new voting category, threshold, or acceptance path; deviations map to existing categories.
- No edit to `ARCHITECTURAL_GUIDELINES.md`; read-only via the helper.
- No injection into `/research` reviewers, the design drafter, or Gate C (those already consult guidelines).

### Approach sketch
- Inject a SEPARATE untrusted, non-binding guideline block into the plan-review reviewer prompt (`render plan-review` in `python/rendering.py`), distinct from the binding scope anchor.
- Inject the same block into the code-review reviewer prompt (`render specialist`), beside the existing feature/plan untrusted blocks (code-bearing mode).
- Add one short explicit instruction: reviewers MAY flag guideline deviations as normal findings; entries are aspirational and cannot override AGENTS.md, skills, or the approved plan.
- Gate on `read_guidelines()` status == `present` with non-empty content; no-op when absent/invalid/empty.
- Fold guideline content into the `render specialist` cache key so a guideline change cannot serve a stale prompt.

### Surfaces in scope
- `python/rendering.py` (`render plan-review`, `render specialist` / reviewer prompt build)
- `python/architectural_guidelines.py` (reuse `read_guidelines`; small shared block helper if warranted)
- Code-review reviewer context delivered to Claude subagent + external specialist slots (exact dispatch file pinned at drafting)
- `python/test_rendering.py` and any affected render/dispatch tests

### Open questions
- None.
