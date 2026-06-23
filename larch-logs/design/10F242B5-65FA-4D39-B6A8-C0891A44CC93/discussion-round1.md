## Decision 1: Dedup scope — all 4 occurrences
- **Question**: The settle-wrapper rc dispatch table appears in 4 site-adapted (not byte-identical) places across 3 files — approval-gates.md (§Shared post-apply pipeline step 8), discussion-rounds.md (Round-2 body), and SKILL.md twice (Gate A + Gate B optional-trailer guards). The issue names only the 2 reference files. Which occurrences point to the single source?
- **Resolution**: Centralize ALL 4 occurrences (including the 2 in SKILL.md) so the table literally "appears once" per the acceptance criterion. Accept the higher edit risk on SKILL.md (halt-rate harness, agent-lint S030 pins).
- **Source**: user

## Decision 2: Canonical home — new shared snippet file
- **Question**: Where should the single canonical rc dispatch table live? It must be site-neutral because rc 0/10/12/13 differ per caller.
- **Resolution**: Add a new small site-neutral reference snippet (e.g. skills/design/references/settle-rc-dispatch.md). Each site references it plus a one-line per-site variant note. Matches the issue's "shared reference snippet" wording.
- **Source**: user

## Hard constraints (must not break)
- **No behavioral change** (acceptance criterion). Runtime LLM behavior at every site must be preserved; rc semantics unchanged. The rc values remain Python-owned (`design_lifecycle.py` emits `POSTPLAN_RC=`); this is doc-hygiene only, not a Python migration.
- Site-specific branches differ and MUST be preserved per site: rc `0` continuation target (Gate B → loop/legacy continuation; discussion-round2 / Gate A → return to Gate A), rc `10` `--site` context (`design Step 3.5 / Gate B` vs `design discussion-round2`), rc `12`/`13` per-caller behavior.
- The /implement dispatch tables (rebase-checkpoint-routing.md, step2-dispatch.md, step-7a.md) are a DIFFERENT table — out of scope.
- The `design-step35-settle.md` script-contract sibling is a separate concern (script contract, not orchestrator prose) — not part of this dedup.
- All linters and harnesses must pass: `make lint`, halt-rate regression, agent-lint (S030 literal-path pins in SKILL.md), markdownlint (MD038/MD037/MD001), and any structural design-skill tests.

## Non-goals
- No logic moved into Python.
- No change to the rc-to-action semantics or the settle wrapper itself.
