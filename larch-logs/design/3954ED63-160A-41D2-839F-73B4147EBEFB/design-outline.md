## Proposed Design Outline

### Goals
- When the main agent is the coder in `/implement` (`--emergency`, both-tools-unavailable fallback, or `--coder claude`), have it produce the dynamic review archetypes so review round 1 stops re-running the separate scout.
- In `/design`, have the plan-proposal drafter (subprocess AND the inline/main-agent fallback) produce the plan-review archetypes, retiring the separate plan-archetype scout on that path.
- Make a failed/absent archetype manifest loud: warn at production time and record the failure in the final report.

### Non-goals
- No change to `/review` standalone — it keeps its Claude-Sonnet scout (no coder/drafter supplies archetypes).
- No change to the existing external Codex/Cursor coder archetype path or the Step 5 consumption contract.
- No change to voting, aggregation, static reviewer panel, or round-cap logic.

### Approach sketch
- `/implement` Step 2.4 (main-agent coding): after implementing, the main agent emits a raw archetype manifest and a mechanical normalize step mirrors the external path (`filter-manifest` + eligibility marker + `step2-scout-coder-status.env`) so Step 5 consumes it identically.
- Gate the separate review-pipeline scout off for the `/implement` Step 5 path via a new flag; `/review` standalone keeps it.
- `/design`: ensure the drafter (subprocess + inline fallback) writes `scout-plan-manifest.json`; retire the separate plan-archetype scout on the design path.
- Failure surfacing: `SCOUT_CODER_STATUS != ok` (or `/design` manifest not produced, excluding by-design docs/test/generated-only skips) → loud bold warning + Warnings entry + dedicated final-report line.

### Surfaces in scope
- `/implement`: `skills/implement/SKILL.md`, `python/implement_dispatch.py`, a new mechanical CLI helper, `python/review_and_fix.py`, `python/review_pipeline.py`, `python/final_report.py` / `python/review_phase_detail.py`.
- `/design`: `python/design_lifecycle.py` / `python/design_postplan.py`, `python/plan_review.py` / `python/plan_review_panel.py`, `python/plan_scout.py`, `skills/design/references/plan-review.md`.
- Shared/contract: `skills/implement/references/step2-dispatch.md`, tests/harnesses.

### Open questions
- Exact final-report surface for the failure line (run-summary field vs. Review Phase Detail). Resolve during plan drafting/review.
