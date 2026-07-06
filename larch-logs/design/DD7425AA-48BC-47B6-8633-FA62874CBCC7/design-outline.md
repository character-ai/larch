## Proposed Design Outline

### Goals
- Promote architectural knowledge from review-only evidence to a tiered feed delivered to the Step 2 coder and to reviewers: invariants (hard constraints) + language-targeted guidelines (judgment).
- Add a thin `ARCHITECTURAL_INVARIANTS.md` (`I-*`) reader that mirrors the existing `G-*` reader and reuses the present/absent/invalid fail-closed contract.
- Make documented `G-*`/`I-*` violations in-scope for reviewers (invariant = blocking; guideline = fix-required-not-OOS) via a `reviewer-templates.md` rubric carve-out.

### Non-goals
- Populating `ARCHITECTURAL_INVARIANTS.md` with real invariants (blank seed lands via #6467 / #6468).
- Any lint/hook/test backstop for invariants (deferred until invariants exist).
- Reader/parser sophistication beyond mirroring the `G-*` reader.

### Approach sketch
- Extend the reader + `cli.py` to also read `ARCHITECTURAL_INVARIANTS.md` as a thin `I-*` mirror; leave `read_guidelines` and its consumers intact.
- Inject invariants + relevant-language guidelines into the Step 2 implementer prompt (Claude + Codex/Cursor) with a mandatory read-order and a one-line acknowledgment; the dispatcher mechanically verifies the acknowledgment (manifest/output field) and warns/fails when missing.
- Feed both files as untrusted content blocks (G-Sec-2) to code reviewers and `/design` plan reviewers; existence-gate every include so a missing file never leaves a dangling read instruction.
- Carve out documented `G-*`/`I-*` violations in `reviewer-templates.md`, then regenerate the four archetypes + pre-rendered variants and pass CI `generate check`.
- Update `SECURITY.md` (new untrusted-input feed) and the `README.md` / `docs` feature surface.

### Surfaces in scope
- `python/larch/core/architectural_guidelines.py`, `python/larch/cli.py`
- Step 2 implementer prompts (`agents/_implementer-base.md`, `agents/codex-implementer.md`, `agents/cursor-implementer.md`) + dispatch/manifest under `python/larch/implement/`
- Reviewer feed: `python/larch/rendering/rendering.py`, `skills/shared/reviewer-templates.md` + generated `agents/reviewer-*.md` / `agents/pre-rendered/`
- Docs: `SECURITY.md`, `README.md`, `docs/`

### Open questions
- Exact manifest/output field and severity (warn vs hard-fail) for a missing acknowledgment: resolve in plan drafting/review.
- Whether external Codex/Cursor coders verify the acknowledgment through the same manifest path (assume uniform) vs. an AGENTS.md-tier-only reference.
