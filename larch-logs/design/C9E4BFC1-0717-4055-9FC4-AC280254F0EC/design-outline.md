## Proposed Design Outline

### Goals
- Convert the existing Step-2 plan-coverage gap from advisory to a graded mechanical gate (firm-heading coverage + non-empty `todos_left`) so a majority-incomplete plan cannot silently reach PR / merge / `[DONE]` / close.
- Middle band force-injects `larch:reviewer-plan-fidelity` into every Step 5 round (exempt from pruning, all tiers); high band hard-gates ship until a recorded scope disposition exists.
- Make completion surfaces (PR body, `[DONE]` rename, final summary) mechanically reflect partial scope.

### Non-goals
- No subjective mid-run scope re-litigation of *what to build*; NEVER #7 stays. Gate is counts, thresholds, and a recorded disposition only.
- No change to external implementer dispatch or the one-shot contract (companion plan-size issue owns oversized plans).
- No coverage measured against implementation-rewritable acceptance inputs (allowlists, baselines, skip markers).

### Approach sketch
- Add middle/high band thresholds to `python/larch/core/config.py` as `Final` with rationale comments; build coverage on the existing untouched-firm-heading probe, materialized at Step 0.
- Persist a durable scope-disposition artifact (frozen dataclass -> tmpdir KV wire file via `larch.io` + run log); `proceed-partial` | `bail-rescope`, never a silent default.
- High band and/or non-empty `todos_left` park the run on an operator `AskUserQuestion` (proceed-partial / bail-rescope) that waits indefinitely and re-fires (no time-out, no unattended default).
- `ship pre-driver` refuses when a disposition is required but unrecorded; `proceed-partial` rewrites PR body (`Part of #N` + deferred inventory), suppresses `[DONE]`, adds the final-summary plan-coverage line, and auto-files a cross-linked follow-up via `/issue`.

### Surfaces in scope
- `python/larch/core/config.py`; `python/larch/implement/dispatch_step2.py` + `dispatch_manifest.py` (coverage/band/`todos_left`).
- Step 5 panel composition (forced plan-fidelity finder); `ship pre-driver`; PR-body and final-report composers; `[DONE]` rename.
- New scope-disposition module + follow-up filing; `docs/workflow-lifecycle.md`; pinning tests across dispatch, panel-composition, PR-body, final-report.

### Open questions
- Exact firm-heading set vs the existing probe (NEW/UPDATED/REWRITTEN firm; MAY_UPDATE conditional/excluded) — resolve in drafting.
- Which `/implement` step hosts the disposition prompt + artifact write (Step 2 vs a dedicated pre-ship gate) — resolve in drafting.
