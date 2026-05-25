## Decision 1: Trigger sources wired to the panel
- **Question**: Which trigger sources should this PR wire the decomposition panel into?
- **Resolution**: All three trigger sources (Step 2b.5 mechanical thresholds + `-p`/`--partition`, Step 1c sprawl heuristic, Step 1d sprawl heuristic). Codebase observation: discussion-rounds.md confirms Step 1c and Step 1d sprawl-heuristic Split branches already converge on Step 2b.5's Split-path body, so wiring all three reduces to replacing the single Split-path body in `skills/design/SKILL.md` Step 2b.5.
- **Source**: user (Step 1c) + codebase (SKILL.md, discussion-rounds.md)

## Decision 2: Filing mechanism for partition pieces
- **Question**: How should the N partition issues be filed?
- **Resolution**: Use the `/larch:issue` Skill (batch mode with `--input-file`, `--intra-batch-deps-file` for inter-piece blocked-by edges, and `--no-dedup` since partition pieces are inherently newly named). Mirrors Step 5b OOS filing in `/design`. Use `/larch:block-issue` (or its underlying `add-blocked-by.sh`) only for edges that cannot be expressed within the batch (none expected on the happy path).
- **Source**: user (Step 1c) + codebase (`/design` Step 5b precedent, `skills/issue/scripts/add-blocked-by.sh`)

## Decision 3: Fate of the original issue after user-approved split
- **Question**: What happens to the original issue?
- **Resolution**: Auto-close with a cross-reference comment. Comment shape matches issue #2644's close-comment (proven shape): brief partition rationale + per-piece bullets with issue number, current state marker (`[DESIGNED]` if a draft plan is included, otherwise "needs `/design`"), short scope sentence, and explicit blocked-by chain. `/design` exits cleanly after close; operator runs `/design` on each new piece independently (no auto-chain).
- **Source**: user (Step 1c) + codebase (#2644 close-comment example)

## Decision 4: Unanimous no-split outcome
- **Question**: If all 4 archetypes recommend `no-split` (panel concludes feature is cohesive), what should happen?
- **Resolution**: Show user a brief "all 4 archetypes voted no-split" summary, then `AskUserQuestion`: `Continue with current plan` / `Force a split anyway (manual partition)` / `Cancel`. User retains final control even when panel agrees with cohesion.
- **Source**: user (Step 1d)

## Decision 5: Cycle check on chosen partition
- **Question**: Should orchestrator validate dependency graph for cycles before filing?
- **Resolution**: Yes — run topological-sort cycle check on the user-chosen (or aggregator-picked) proposal's dependency graph before filing. If a cycle is found, refuse to file and `AskUserQuestion`(`pick another proposal` / `cancel`). Cheap defense against reviewer hallucination on the "independently mergeable" claim.
- **Source**: user (Step 1d)

## Decision 6: Panel-itself tier-gating
- **Question**: Should the decomposition panel itself be tier-gated (match parent /design's tier), or always run the full 8-reviewer panel?
- **Resolution**: Always run the full 4-archetype × 2-vendor (= 8 reviewer slots) panel regardless of the parent `/design`'s tier (`--trivial` / `--simple` / `--hard`). Partition is a high-stakes one-shot decision affecting multiple downstream PRs; the full panel cost is justified. Matches the issue body literally.
- **Source**: user (Step 1d)

## Decision 7: Reviewer-failure tolerance inside the panel
- **Question**: What's the panel-failure contract when external reviewers fail (after Cursor → Codex → Claude waterfall exhausts)?
- **Resolution**: Mirror `/design` Step 3 plan-review-loop semantics. Each slot uses `dispatch-with-waterfall.sh` (Cursor → Codex → Claude). The panel emits a `DEGRADED_PANEL` flag when any slot fell back. If 0 reviewer slots return usable proposals, surface a fatal "panel-failed" status and surface to the operator with `AskUserQuestion`: `Retry panel` / `Cancel`. If at least 1 reviewer returns a usable proposal, present what arrived (label degraded archetypes in the AskUserQuestion option descriptions).
- **Source**: codebase (`plan-review-loop.sh` `DEGRADED_PANEL` / `LOOP_STATUS=panel-failed` precedent)

## Decision 8: Auto-chain `/design` on filed partition pieces
- **Question**: After filing N partition issues, should `/design` auto-chain on the new issues or exit?
- **Resolution**: Exit cleanly. The operator runs `/design` independently on each new issue. Matches the issue body literally ("User runs `/design` on each new issue independently. Matches what was done for #2644.").
- **Source**: issue body
