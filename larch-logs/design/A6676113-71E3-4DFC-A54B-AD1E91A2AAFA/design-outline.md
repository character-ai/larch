## Proposed Design Outline

### Goals
- Add a Python-owned `design render-gate` command that emits the exact AskUserQuestion question/header/option copy for Gates A, B (default/auto-apply path), and C, byte-identical to current text.
- Shrink `approval-gates.md` to loop semantics, entry/re-entry guards, resume idempotency, and the cross-gate state-invariants contract; remove the literal prompt copy the renderer now owns.
- Preserve exact gate behavior and wording (fixture-diffed); keep `scripts/test-design-structure.sh` passing, updating pins that assert copy now owned by Python.

### Non-goals
- `approval-gates-explicit.md` (Gate B `--per-round-approval` chooser) stays untouched — already conditional-only, outside the eager closure this issue targets.
- `settle-rc-dispatch.md` / `step2b5-rc-handling.md` dispatch-table rendering — sibling issue #5985's separate scope.
- No behavior change to gate routing, review-round cap logic, or severity classification (already Python-owned since #5157). This is a copy relocation, not a redesign.

### Approach sketch
- Extend the existing Gate-B rendering home (`plan_review_loop.py`, already hosting `gate_b_counts` / `gate_b_finding_line` / `preview`) with gate-copy emitters for A and C, registered as `design`-domain CLI verb(s) per the repo's `(domain, verb)` → `module.main` convention.
- Emit KV pairs (question text, header, option label/description strings, conditionals like cap-reached or panel-failure already resolved) mirroring `gate_b_finding_line`'s composed-string style, so the orchestrator relays fields straight into `AskUserQuestion` instead of composing from prose.
- `approval-gates.md` keeps short "run the render command, bind these KVs, fire `AskUserQuestion` with these exact fields" pointers in place of today's inline copy blocks.

### Surfaces in scope
- `skills/design/references/approval-gates.md`
- `python/larch/review/plan_review_loop.py` (or a sibling module) plus the `python/larch/cli.py` verb registry
- `python/tests/review/test_plan_review.py` (or a new gate-rendering test module)
- `scripts/test-design-structure.sh`

### Open questions
- None.
