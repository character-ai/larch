## Decision 1: Brainstorm Codex role (scope)
- **Question**: The Problem statement lists brainstorm as a Codex call site, but the operator Decisions only assign review/vote/fix to the cheap bucket. Which model should brainstorm use?
- **Resolution**: Keep brainstorm unchanged — it stays on the strong implementer key (`LARCH_CODEX_MODEL` / gpt-5.5). Brainstorm is out of scope for cheap routing. Only reviewers, voters, and fix-appliers move to the cheap bucket.
- **Source**: user

## Decision 2: Voter Codex-unavailable fallback (Part C)
- **Question**: When Codex is absent, where do the pragmatism and plan-fidelity voters (newly moved to Codex/mini) fall back?
- **Resolution**: Fall back to Cursor / composer-2.5 (where the validity voter already runs), matching reviewer fallback convention (Codex → Cursor). Drop to a Claude subagent voter only if both vendors are down.
- **Source**: user

## Decision 3: Env key surface (Part A)
- **Question**: Should review/vote/fix share one cheap-bucket env key, or get separate per-role keys?
- **Resolution**: Separate per-role keys, one per role, each defaulting to `gpt-5.4-mini`. Proposed names (to confirm at outline/Gate C): `LARCH_CODEX_REVIEW_MODEL` (reviewers), `LARCH_CODEX_VOTE_MODEL` (the two voters), `LARCH_CODEX_FIX_MODEL` (fix-appliers). Distinct from the implementer's strong `LARCH_CODEX_MODEL`.
- **Source**: user

## Decision 4: Implementer stays strong (hard constraint)
- **Question**: Does the Step 2 Codex implementer change model?
- **Resolution**: No. The implementer keeps the strong key (`LARCH_CODEX_MODEL` / gpt-5.5). This is the whole reason per-role routing is needed instead of a global model flip.
- **Source**: user (operator-confirmed in issue)

## Decision 5: Per-role routing must survive a global override (hard constraint)
- **Question**: A global `LARCH_CODEX_MODEL` currently overrides per-call `--default-model`. How must per-role routing behave under that?
- **Resolution**: Review/vote/fix roles must resolve their own cheap-bucket key even when `LARCH_CODEX_MODEL` is set globally. The global strong key must not silently re-upgrade the cheap roles. Behavior change to document: a globally-set `LARCH_CODEX_MODEL` now affects only the implementer (and brainstorm), not reviewers/voters/fixers.
- **Source**: user (operator-confirmed in issue) + codebase precedence note

## Decision 6: Host Mini on Codex only (constraint)
- **Question**: Should the cheap model run on Codex or Cursor?
- **Resolution**: Host `gpt-5.4-mini` on Codex only. Cursor's token floor makes Cursor+mini the most expensive option. Leave Cursor reviewers/voters on `composer-2.5` unchanged.
- **Source**: user (operator-confirmed in issue)

## Decision 7: Sequencing against conflict umbrellas (constraint)
- **Question**: Issue flags packaging umbrella #4982 (parts #5167-#5175 relocate agents.py / review_pipeline.py / plan_review.py / report_tokens_cost.py) and keyword-args umbrella #5002 as touching the same files.
- **Resolution**: Proceed now with awareness; note the conflict surface in the plan so /implement can rebase. Do not block on the umbrellas. Keep edits surgical and localized to minimize merge conflicts.
- **Source**: user (operator-confirmed in issue) + codebase
