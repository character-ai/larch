## Acceptance

- `make lint` passes (agent-lint S030 path pins, the drift-prone-prose rule, and markdownlint all green).
- `skills/design/SKILL.md` no longer enumerates `Arch`, `Innovation`, `Pragmatic`, or `Requirements` in the opening summary, the Step 3 IMPORTANT block, or the spawn-order line.
- The opening summary no longer contains `full static diagonal`, `rounds 2-5`, or `review reviewer-prune`, and `as documented in this file` is replaced with an explicit `plan-review.md` back-reference.
- The Step 3 `MUST ALWAYS run the full Step 3 panel` directive, `Never skip or abbreviate`, the slowest-first spawn order, and all three fallback rules (Cursor falls back to Codex, Codex to Cursor, both-absent to Claude) remain intact.
- The Step 3 MANDATORY normative-source line keeps every S030 literal-path pin and now also names panel topology and static slot identity.
- `skills/design/references/plan-review.md` authorizes panel topology and static archetype identity in both Consumer and When-to-load; its Contract closing sentence no longer restricts prompt-side loads to judgment and artifact contracts only; a Static-slots subsection names `arch`, `innovation`, `pragmatic`, and `requirements` with focus labels.
- No edits to `scout-plan-archetypes-prompt.txt`, `python/rendering.py`, `python/plan_review.py`, `python/plan_review_panel.py`, `skills/shared/topology.tsv`, `docs/topology.md`, or `docs/review-agents.md`; `docs/topology.md` is not regenerated because panel counts do not change.
- No runtime behavior change to the plan-review panel.

diff_lines: 49
