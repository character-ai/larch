## Decision 1: Codex vendor scope on the code-review panel
- **Question**: How far should Codex extend when added to the `/review` code-review panel (currently Codex is hard-disabled via `codex_present_for_waterfall="false"`)?
- **Resolution**: **Static + dynamics (full both-vendor mirror)**. Each of the 4 collapsed static archetypes gets both a Cursor and a Codex slot (8 static), and each scouted dynamic archetype gets both a Cursor and a Codex slot. Re-enable Codex in the panel waterfall (`--codex-present "$CODEX_AVAILABLE"` instead of forced `false`), gated on `CODEX_PRESENT`/availability. Mirrors `/design`'s `dispatch-plan-review-panel.sh` both-vendor emission.
- **Source**: user

## Decision 2: Merged-lane archetype slugs / attribution labels
- **Question**: After collapsing 6 archetypes → 4, what slugs should the two merged lanes use (tally-code-votes.sh attribution + future #3463 pruner key on these)?
- **Resolution**: **Keep anchor slugs.** The 4 archetypes are: `security` (standalone), `correctness` (standalone), `edge-cases` (primary lens; folds `structure` in as a secondary "flag only critical" scan), `testing` (primary lens; folds `plan-fidelity` in as a secondary scan). The `structure` and `plan-fidelity` slugs retire from the panel. Security + correctness slugs unchanged.
- **Source**: user

## Decision 3: In-scope surface (what this change touches)
- **Question**: Which files form the in-scope surface?
- **Resolution**:
  - `skills/review/scripts/dispatch-panel.sh` — `cursor_specialists` list → 4 archetypes; emit Codex static twins (gated on availability); emit Codex dynamic twins; flip `codex_present_for_waterfall`; update the reserved-slug list (lines ~199-202).
  - `scripts/scout-dynamic-archetypes.sh` — update the reserved-slug list (lines ~537-538) to the new 4 slugs so the scout never proposes a dynamic archetype colliding with a static slug.
  - `skills/shared/reviewer-templates.md` — define/extend the `edge-cases` (primary + structure secondary) and `testing` (primary + plan-fidelity secondary) combined prompts following the existing primary-lens + "secondary scan, flag only critical" pattern; regenerate any generated `agents/*.md`.
  - `agents/reviewer-edge-cases.md`, `agents/reviewer-testing.md` (and any generated agent files) — Claude-fallback prompts updated to cover the secondary scan.
  - `skills/review/scripts/tally-code-votes.sh` — focus-area map (lines ~288-293) and attribution narrowed to the 4 slugs; verify `codex-specialist-*-output.txt` slot parsing (already present at ~line 320) covers Codex static twins.
  - `docs/review-agents.md` and any prose referencing the 6 archetypes.
- **Source**: codebase + issue

## Decision 4: Hard constraints — what must NOT break
- **Question**: What existing behavior must be preserved?
- **Resolution**:
  - **Plan-fidelity coverage must survive the merge.** `dispatch-panel.sh` requires `--plan-file` and the plan-fidelity lane is "always dispatched"; folding plan-fidelity into `testing` must keep plan-conformance checking and the plan-file requirement intact.
  - **Shared agent files must not be deleted.** Retired specialist agents (`reviewer-structure.md`, `reviewer-plan-fidelity.md`) are registered larch subagents referenced by reserved-slug lists and docs; remove them from the panel's reference set but do not delete the files unless confirmed orphaned (KARPATHY surgical-change rule). Mention, don't delete.
  - **CI must stay green**: `agent-sync` (`scripts/check-generators.sh`), `check-focus-area-enum.sh` (focus-area enum anchor in dispatch-panel.sh), and reviewer-template→agent regeneration.
  - **Both reserved-slug lists kept in sync** (dispatch-panel.sh + scout-dynamic-archetypes.sh).
  - **Waterfall fallback semantics preserved**: every slot still produces output (Cursor→Codex→Claude); re-enabling Codex must not break the Claude Phase-3 backstop.
- **Source**: codebase

## Decision 5: Out of scope / non-goals
- **Question**: What is explicitly NOT part of this change?
- **Resolution**:
  - **#3463 conditional spawning / aggressive pruning** — deferred; this change "hits harder upfront" and #3463 prunes later, keying on the 4-archetype attribution labels established here.
  - **`/design` plan-review driver** (`run-step3-review.sh`, `dispatch-plan-review-panel.sh`) — untouched; independent surface.
  - **Post-change validation** (re-mining run logs after ~1 week to confirm catch-rate holds) — a follow-up activity, not implementation work.
- **Source**: issue
