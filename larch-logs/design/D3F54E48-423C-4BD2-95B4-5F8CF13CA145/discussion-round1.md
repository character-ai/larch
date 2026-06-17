## Decision 1: Scope of non-reviewer rows in the round Gantt
- **Question**: How far should "other agents that ran in the round" extend beyond the fix-applying coder?
- **Resolution**: Always chart the fix-applying coder (codex/cursor apply in /implement and /review; `plan revise-waterfall` vendor in /design). Chart other round agents (coder scout, main-agent vote adjudication) ONLY where a chartable `type=vendor` timing row already exists. Do NOT add heavy new instrumentation for agents that emit no vendor row today (e.g. main-agent vote adjudication, which is the main Claude agent, not a vendor subprocess).
- **Source**: user

## Decision 2: Post-apply CI/verification rows
- **Question**: Should post-apply CI-fix / CI-test rows (currently filtered by `skip_gantt_row`) also appear in the round Gantt?
- **Resolution**: Keep CI-fix/CI-test rows excluded. The round chart shows agents (reviewers + aggregator + voters + apply coder + any other genuine agents), not verification passes. Preserve the renderer's existing "no CI noise" intent and the 25-row cap. Charting the apply coder already fills most of the observed gap.
- **Source**: user

## Decision 3: #4537 ordering dependency
- **Question**: Does this work still need to wait on / block against #4537 (restores these charts to the final reports)?
- **Resolution**: No. #4537 already merged (commit `7d0035550`). The Gantt charts already render in final reports via `python/review_phase_detail.py` -> `scripts/render-review-phase-detail.sh`. No open `/block-issue` edge remains to express. The original report's "express dependencies with /block-issue" instruction is satisfied (only candidate blocker is closed).
- **Source**: codebase

## Decision 4: Hard constraints to preserve
- **Question**: What existing behavior must not break?
- **Resolution**: Preserve the renderer's best-effort contract (degrade to what it can render, exit 0, never break the final report; usage errors exit 2). Preserve existing reviewer/aggregator/voter charting, the per-round table, top-N reviewers, failed-slot counts, and the 25-row Gantt cap. The same renderer feeds the live `p` progress report (`python/progress_report.py`) and both final reports, so the fix applies uniformly across /implement, /review, /design with one renderer change plus apply-row emission.
- **Source**: codebase
