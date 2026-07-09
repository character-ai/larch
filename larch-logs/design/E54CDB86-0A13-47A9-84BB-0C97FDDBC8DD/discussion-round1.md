## Decision 1: Fate of the `plan-fidelity-forced` lane
- **Question**: When we remove the one-off `plan-fidelity-auto` slot (#6553), what happens to the related `plan-fidelity-forced` auto row in `review_dispatch_panel.py`, which shares the `reviewer-plan-fidelity.md` profile and the `auto` model?
- **Resolution**: KEEP it. It is a distinct, one-day-old (#6526) conditional `/implement` safeguard that fires only on low plan-coverage diffs (`PLAN_FIDELITY_FORCED=true` when band ∈ {middle, high}). It already runs on Cursor/`auto`, which is consistent with this issue's goal. Only change required: repoint its Codex-fallback `codex_review_model_role_for_archetype("review.panel", "plan-fidelity-auto", tier)` call off the deleted `plan-fidelity-auto` archetype name (behavior-preserving; still resolves to `"review"`). Do NOT remove `_append_forced_plan_fidelity_row` or the `PLAN_FIDELITY_FORCED` plumbing.
- **Source**: user

## Decision 2: Model-swap scope (from the issue; hard constraints)
- **Question**: Which reviewer lanes swap Composer 2.5 → `auto`, and which stay on Composer 2.5?
- **Resolution**:
  - SWAP to `auto` (per-slot override): Code-review panel (`review.panel`) Cursor lanes — correctness, edge-cases, testing, and dynamic Cursor lanes. Plan-review panel (`design.plan_review_panel`) Cursor lanes — arch, innovation, pragmatic, requirements, and dynamic Cursor lanes.
  - STAY on Composer 2.5: `CURSOR_DEFAULT_MODEL = "composer-2.5"` is unchanged. Voter slots (`review.voters`, `design.plan_voters`) and Cursor coder/implementer/fixer roles (`implement.step2_coder`, `review.fix_coder`, and peers) read the default and must remain on Composer 2.5.
- **Source**: codebase + issue

## Decision 3: Remove the #6553 one-off lane
- **Question**: What to do with the `plan-fidelity-auto` slot added in #6553?
- **Resolution**: Drop the `plan-fidelity-auto` `SlotDefault` from `review.panel` in `config.py` and its per-slot model plumbing (the `is_additive_plan_fidelity` special-casing in `_append_static_specialist_rows`, and orphaned tally/timing references). It was an always-on additive A/B lane, now redundant once all Cursor reviewers move to `auto`.
- **Source**: issue

## Hard constraints / invariants to preserve
- `CURSOR_DEFAULT_MODEL = "composer-2.5"` MUST NOT change.
- Cost attribution: keep `resolved_model` (progress display) and the launched `--model` in sync so `BUCKETS_cursor_by_model` continues to bucket reviewer usage under `auto` vs `composer-2.5`.
- `--no-fallback` panel semantics and existing slot identities (names/outputs) for non-swapped lanes stay intact.
