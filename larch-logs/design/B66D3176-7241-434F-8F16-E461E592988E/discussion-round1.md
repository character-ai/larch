# Discussion Round 1 — scope decisions

Feature: bug-treadmill [FEATURE] analyze-bugs: chronic-zone analytics + risk-routed deep queue (issue #6970).

The feature description is prescriptive (9 design points, explicit thresholds, explicit non-goals). Two scope-affecting ambiguities were resolved in Step 1c. No additional scope branches require discussion; remaining choices are implementation approach and belong to Step 2b drafting and Step 3 review.

## Decision 1: Chronic-zone "2+ connected by chain edges" semantics
- **Question**: Design point #4 says a zone is chronic if it has "2 or more connected by chain edges." What does "connected" mean?
- **Resolution**: Any chain edge in zone. A zone is chronic if 2+ of its bugs are endpoints of any chain edge (to any issue, in or out of the zone). Catches cross-zone residual chains like #6882 to #6898.
- **Source**: user

## Decision 2: "Since last run" delta computation source
- **Question**: The ledger is append-only and cumulative, so the delta needs a notion of "previous run." How should it be computed?
- **Resolution**: Per-run snapshot file. Each run writes a run-state.json snapshot (selected issues, verified issues, chronic zones, chain edges). The next run diffs current vs the most recent prior snapshot for the same repo. First run emits a "first run" delta with empty deltas.
- **Source**: user

## Hard constraints (from issue, binding on the plan)
- Preserve the whole-line `KEY=value` stdout grammar and the `ANALYZE_BUGS_COST_ESTIMATE` line unchanged.
- Coordinator-side only: `python/larch/issue/analyze_bugs.py` plus `.claude/skills/analyze-bugs/SKILL.md`. No bundle-format or agent-prompt changes.
- Keep the `--deep-max` cap; log dropped candidates instead of truncating silently.
- `--sample` defaults to 3; the report always prints the triage false-pass rate.

## Non-goals (from issue)
- No new agents, no bundle-format changes, no sweep stage, no runtime execution. Those are sibling bug-treadmill issues.

## Resolved decisions
2
