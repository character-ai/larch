## Proposed Design Outline

### Goals
- Execute #6162 round 1 (design-only): drop the design eager closure by demoting eager references the repaired heatmap shows are never read on the green path.
- Cite the heatmap row (~0/70 reads) for each demotion; confirm the eager-closure token drop via the closure-growth ratchet.

### Non-goals
- No implement-side demotions this round (read-attribution undercounted post-#6263; deferred).
- No demotion of well-read refs (all measured ≥47%) or already-conditional refs (`validator-failure.md`).
- No compaction-resilience demotion (anti-halt / NEVER blocks stay eager); no panel/round/turn-structure change; reference file bodies byte-preserved.

### Approach sketch
- Demote the two never-read eager-closure members by rewording/scoping their `skills/design/SKILL.md` load directives so the closure scanner no longer counts them as eager:
  - `SKILL.md:112` → `skills/shared/external-reviewers.md` (Step 0a degraded-tools gate; Python-owned, branch handling already inlined) — scope to the `needs-degraded-decision` branch or convert to a non-Read contract pointer.
  - `SKILL.md:99` → `skills/shared/session-setup-output.md` (Step 0a setup KVs; parse list already inlined) — convert to a contract pointer.
- Keep the referenced files byte-identical; only SKILL.md load-directive wording changes.
- Verify the closure-growth lint recomputes a lower design eager closure.

### Surfaces in scope
- `skills/design/SKILL.md` (two load-directive lines, ~99 and ~112)
- `python/larch/lint/lint_skill_closure_growth.py` — recompute/ratchet verification only (no rule change unless required to bank the drop)
- No change to `external-reviewers.md` / `session-setup-output.md` bodies

### Open questions
- Exact rewording that (a) drops eager-closure membership per the scanner's directive detection and (b) preserves the degraded-path contract for `external-reviewers.md` — settle in Step 2b; must not remove a genuinely-needed conditional reference or trip the closure lint's own directive checks.
