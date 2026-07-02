## Decision 1: Scope boundary — approval-gates-explicit.md
- **Question**: Should Python rendering also cover `approval-gates-explicit.md` (Gate B `--per-round-approval` explicit chooser + one-by-one prompts), or stay scoped to `approval-gates.md`?
- **Resolution**: Scope to `approval-gates.md` only. `approval-gates-explicit.md` is already excluded from the eager closure (conditional load, #5692); the issue's Scope text and acceptance criteria name only `approval-gates.md`. Leave it as static prose for a future issue.
- **Source**: user (no response within wait window; proceeding with recommended default per orchestrator judgment) — revisit if the operator corrects this.

## Decision 2: Out-of-scope adjacent files
- **Question**: Does this issue also touch `settle-rc-dispatch.md`, `step2b5-rc-handling.md`, `plan-review.md`, or `finalize-step5.md`?
- **Resolution**: No. `settle-rc-dispatch.md` / `step2b5-rc-handling.md` dispatch-table rendering is sibling issue #5985's separate scope. `plan-review.md` / `finalize-step5.md` / `discussion-rounds.md` / `design-outline.md` prose-density is separate round-X/XI issues. This issue touches only `approval-gates.md`, its Python renderer, `scripts/test-design-structure.sh`, and gate harness fixtures/tests.
- **Source**: codebase research (round XI umbrella #5986, sibling issues #5984/#5985).

## Decision 3: Wording fidelity
- **Question**: Can gate copy be lightly reworded while moving it into Python, or must it stay byte-identical?
- **Resolution**: Byte-identical. The issue's acceptance criterion is explicit: "Gate behavior and wording identical (fixture-diffed)." This is a verbatim-move, not a rewrite.
- **Source**: issue #5983 text (explicit).
