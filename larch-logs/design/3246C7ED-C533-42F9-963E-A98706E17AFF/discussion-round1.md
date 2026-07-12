# Discussion Round 1 — Issue #7018

Feature: add a specialist review archetype for architectural guidelines and invariants compliance, and stop feeding guidelines/invariants to the other reviewer archetypes.

## Decision 1: Stop-feed scope (reviewers only)
- **Question**: Should “stop feeding guidelines/invariants to other archetypes” apply only to the reviewer panel, or also to the /implement Step 2 coder and /design plan drafter (which receive them to honor while authoring)?
- **Resolution**: Reviewer panel only. The /implement coder feed (`_ci_launcher._architectural_knowledge_block`) and the /design drafter feed (`design_step2b`) stay; the implementer’s `architectural_acknowledgment` manifest requirement stays. Only the reviewer-archetype feed is removed.
- **Source**: user

## Decision 2: /design integration (augment Arch, no new archetype)
- **Question**: How should the compliance specialist integrate with /design plan review?
- **Resolution**: Do NOT add a new reviewer archetype to /design. Instead augment the existing inline “Arch” plan-review personality’s responsibilities to validate that architectural guidelines and invariants are not violated. Arch must receive the guidelines/invariants content to perform this check.
- **Source**: user

## Decision 3: Dead carve-out language (remove + regen)
- **Question**: Should the embedded “Documented architectural carve-out” (I-*/G-*) paragraph be removed from the non-compliance reviewer templates?
- **Resolution**: Yes. Strip the carve-out from all reviewer templates except the new compliance specialist; regenerate the generated `agents/reviewer-*.md` files; update `reviewer-templates.md` and `topology.tsv`.
- **Source**: user

## Decision 4: Feed mechanism location (codebase)
- **Question**: Where is the “fed guidelines and invariants” mechanism for reviewers, and where are the per-difficulty panel slots?
- **Resolution**: `python/larch/rendering/rendering.py::_render_specialist_text` appends `_architectural_guidelines_review_section` to every specialist reviewer (line ~949). That section reads invariants always and guidelines for non-TRIVIAL tiers (lines ~825–851). This single call site is the gating point. Per-difficulty panel slots live in `python/larch/core/config.py`: `_CODE_REVIEW_ARCHETYPES = ("correctness","edge-cases","testing")` for /review + /implement Step 5, and `_PLAN_REVIEW_ARCHETYPES = ("arch","innovation","pragmatic","requirements")` for /design inline personalities.
- **Source**: codebase

## Decision 5: Generated vs hand-maintained agent files (codebase)
- **Question**: Which `agents/reviewer-*.md` are generated vs hand-maintained, and how do they stay in sync?
- **Resolution**: `code-reviewer.md`, `reviewer-plan-fidelity.md`, `reviewer-code-robustness.md`, `reviewer-security-structure-tests.md` are GENERATED from `skills/shared/reviewer-templates.md` via `scripts/generators.tsv` (`python3 python/cli.py generate <verb>`; sync enforced by `generate check`). The others (`reviewer-structure`, `reviewer-security`, `reviewer-testing`, `reviewer-correctness`, `reviewer-edge-cases`) are hand-maintained with pre-rendered bodies (`agents/pre-rendered/*-body.txt`, refreshed via `generate pre-rendered-reviewer-prompts`). Whether the new compliance specialist is generated or hand-maintained is a Step 2b decision.
- **Source**: codebase

## Non-goals (carried from issue + answers)
- Do not stop feeding guidelines/invariants to the /implement coder or /design drafter.
- Do not add a new archetype to /design plan review (augment Arch instead).
- Do not change the implementer’s `architectural_acknowledgment` manifest contract.
