## Proposed Design Outline

### Goals
- Slim the always-loaded /design anti-halt preamble: point its generic core at `subskill-invocation.md#anti-halt`, keep only /design-specific deltas.
- Dedup the final-summary "Binding:" block: state the verbatim/no-recap rule once in the always-loaded preamble stub; have the 4 finalize sites cite it and name only the per-site source.
- Add the recap-prohibition + no-cost-paraphrase rule once to `final-summary-emit.md` Shared rules.

### Non-goals
- No `skills/implement/SKILL.md` edit; NEVER #17 stays intact (it already references the shared file).
- Do not re-touch the Monitor/polling/recovery-contract lines (settled by #5405 in `orchestrator-never.md`).
- No determinism regression: never swap an always-loaded directive for a bare lazy-read pointer.

### Approach sketch
- Determinism-safe DRY (the #5405 stub pattern): keep one compact always-loaded operative stub per directive; move only verbose mechanics/rationale to the shared lazy-read files.
- Sequence: binding dedup first (low risk), then the anti-halt anchor; both edit the same preamble line.
- Anti-halt: add `→ subskill-invocation.md#anti-halt` pointer; trim only generic boilerplate identical to the shared core; keep deltas (step chain, brainstorm/outline yield, Gate re-entries, "plan is intermediate").
- Finalize: collapse the 4 restatements (cancellation, Step 5c abort, Step 5c item-5, Step 5d) to compact citations of the preamble rule plus the per-site source.

### Surfaces in scope
- `skills/design/SKILL.md` — preamble plus finalize region.
- `skills/shared/final-summary-emit.md` — Shared rules: add the recap-prohibition rule.
- `skills/shared/subskill-invocation.md` — `#anti-halt` reference target (content edit TBD).
- `scripts/test-design-structure.sh` — harness pins may need updating for relocated/collapsed literals.

### Open questions
- Does `subskill-invocation.md` need a content edit (note /design as an anchor consumer outside the banner-harness scope), or is it purely the reference target?
- Which `test-design-structure.sh` pins assert the collapsed restatements, and how much harness update is required? Verify with `make test-design-structure` and `make lint`.
