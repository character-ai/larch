## Decision 1: scout manifest path for /design
- **Question**: Where does the drafter write the scout manifest, and how does plan-review-loop.sh pick it up?
- **Resolution**: Drafter writes `$DESIGN_TMPDIR/scout-plan-manifest.json` (same path that plan-review-loop.sh and dispatch-plan-review-panel.sh already read today). plan-review-loop.sh removes its own scout call and relies on the pre-populated manifest.
- **Source**: codebase (dispatch-plan-review-panel.sh line 150, plan-review-loop.sh lines 877-885)

## Decision 2: scout manifest path for /implement
- **Question**: Where does the Step 2 coder write the scout manifest, and how does dispatch-panel.sh read it?
- **Resolution**: Coder writes a scout sidecar to `$IMPLEMENT_TMPDIR/scout-coder-manifest.json`. `dispatch-panel.sh` gains a `--pre-scouted-manifest FILE` flag; when provided and valid, it skips the scout call and uses the supplied manifest. `run-step5-review.sh` threads this flag through `review-and-fix.sh` → `review-core.sh` → `dispatch-panel.sh`.
- **Source**: codebase (dispatch-panel.sh scout invocation block; review-core.sh `--dynamic-archetypes` flag threading)

## Decision 3: impact on standalone /review
- **Question**: Does removing scout from dispatch-panel.sh break standalone /review?
- **Resolution**: Standalone /review is NOT affected. The `--pre-scouted-manifest` flag is optional; when absent, dispatch-panel.sh runs scout as before. This preserves existing /review behavior.
- **Source**: codebase (dispatch-panel.md; scout is triggered by `--dynamic-archetypes N > 0` in dispatch-panel.sh)

## Decision 4: inline drafting fallback for /design
- **Question**: If Step 2b inline drafting is used (drafter subprocess fails), no scout manifest is produced. Is that acceptable?
- **Resolution**: Yes. The inline drafting path produces no scout manifest; plan-review-loop.sh proceeds with no dynamic archetypes. This is fail-open behavior consistent with the current scout fail-open contract.
- **Source**: user response (remove entirely, no fallback)

## Decision 5: claude coder fallback for /implement
- **Question**: If Step 2 coder is Claude (main agent, not Codex/Cursor), does it produce a scout manifest?
- **Resolution**: Claude coder does not produce a scout sidecar. The `--pre-scouted-manifest` flag is absent from the run-step5-review call, and dispatch-panel.sh runs scout per-round as before on the Claude coder path. This preserves dynamic archetypes for Claude-only runs.
- **Source**: codebase (ORCHESTRATOR_EDIT_AUTHORITY=allowed means Claude coder; coder=claude path has no manifest)

## Decision 6: output format compatibility
- **Question**: Should the drafter/coder produce the same JSON format as scout-dynamic-archetypes.sh?
- **Resolution**: Yes. The drafter and coder each write `{"archetypes":[...]}` matching the existing schema. dispatch-plan-review-panel.sh and dispatch-panel.sh already validate this format; no schema change needed.
- **Source**: codebase (dispatch-plan-review-panel.sh lines 260-286; scout-plan-archetypes-prompt.txt schema)

## Decision 7: drafter prompt extension
- **Question**: How does the drafter (Codex/Cursor) know to produce the scout JSON?
- **Resolution**: The drafter prompt (or the agent-prompt file used by launch-codex-implement.sh / launch-cursor-implement.sh for the drafter path) is extended with a section instructing the model to additionally write `$DESIGN_TMPDIR/scout-plan-manifest.json` with up to 3 dynamic archetypes. Fail-open: if not produced, plan-review-loop.sh continues without dynamic archetypes.
- **Source**: codebase (LARCH_CODEX_AGENT_PROMPT / LARCH_CURSOR_AGENT_PROMPT plumbing; design-step2b-drafter.sh)
