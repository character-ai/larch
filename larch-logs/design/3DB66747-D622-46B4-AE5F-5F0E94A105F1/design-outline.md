## Proposed Design Outline

### Goals
- Run scout once per /design or /implement run instead of per review round.
- Produce scout archetype output inline in the Step 2b drafter (design) and Step 2 coder (implement) subprocesses.
- Remove the separate per-round scout agent spawns from plan-review-loop.sh and dispatch-panel.sh on the implement path.

### Non-goals
- Do not change standalone /review scout behavior (dispatch-panel.sh still scouts per round for /review).
- Do not delete scout-plan-archetypes-wrapper.sh or scout-dynamic-archetypes.sh; they remain for /review.
- Do not change the scout JSON schema.
- Do not add a fallback scout invocation when the drafter or coder fails to produce a manifest.

### Approach sketch
- Extend the Step 2b drafter subprocess prompt to also write `$DESIGN_TMPDIR/scout-plan-manifest.json` (same format as scout-dynamic-archetypes.sh).
- Remove the scout-plan-archetypes-wrapper.sh call from plan-review-loop.sh `_run_plan_review_round`; dispatch-plan-review-panel.sh already reads the fixed path.
- Add `--pre-scouted-manifest FILE` to dispatch-panel.sh; when set, skip the internal scout call and use the provided manifest.
- Extend the Step 2 implementer prompt (codex/cursor) to write `$IMPLEMENT_TMPDIR/scout-coder-manifest.json`.
- Thread `--pre-scouted-manifest` from run-step5-review.sh through review-and-fix.sh, review-core.sh, and dispatch-panel.sh.

### Surfaces in scope
- `skills/design/scripts/plan-review-loop.sh` — remove per-round scout call
- `skills/design/scripts/design-step2b-drafter.sh` — produce scout manifest as additional drafter output
- `skills/review/scripts/dispatch-panel.sh` — add `--pre-scouted-manifest` optional flag
- `scripts/run-step5-review.sh` — thread pre-scouted manifest from IMPLEMENT_TMPDIR
- `skills/review-and-fix/scripts/review-and-fix.sh` — forward pre-scouted manifest flag to review-core.sh
- `skills/review/scripts/review-core.sh` — forward pre-scouted manifest flag to dispatch-panel.sh
- Sibling .md files for each changed script

### Open questions
- None.
