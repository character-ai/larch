# Design Discussion — Round 1 (scope and constraints)

Issue #5544: Wire Option A voter prompt-feedback incentive. Partition piece 1 of 2 from #5537.

## Decision 1: Rollout gating
- **Question**: How should the calibration-feedback injection be gated?
- **Resolution**: Default ON for every voter dispatch, with a single env kill-switch to disable (e.g. `LARCH_VOTER_CALIBRATION_FEEDBACK=0`). On-by-default is required so the acceptance criterion (measurable High Rate drop over the incentivized-era corpus) is reachable; the kill-switch gives a clean rollback and a corpus-era boundary.
- **Source**: user

## Decision 2: Calibration signal window
- **Question**: What window of committed run logs feeds each tool's recent High Rate / Calibration Score?
- **Resolution**: Bounded recent window = the **last 100** committed run-log directories by run-id recency (most recent first), rolled up per tool. Fall back to all-history when fewer than 100 exist. Window size is env-tunable with default 100 (e.g. `LARCH_VOTER_CALIBRATION_WINDOW=100`).
- **Source**: user

## Decision 3: Panel scope
- **Question**: Which dispatch paths get calibration feedback?
- **Resolution**: Both panels. Code-review voters (`cursor-validity`, `codex-plan-fidelity`, `codex-pragmatism` in `python/agent_voters.py`) and plan-review voters (`claude`, `codex`, `cursor` in `python/plan_review_panel.py`). Both call `render voter`.
- **Source**: issue + codebase

## Decision 4: Roll-up granularity
- **Question**: At what granularity is the signal computed?
- **Resolution**: Per **voter tool** (`claude` / `codex` / `cursor`), aggregated across panels. Map each slot label to its tool, then roll up. Reuse `compute_voter_severity_distribution` and `severity_calibration_score` from `python/voting.py`; do not reimplement the severity math.
- **Source**: issue + codebase

## Decision 5: Ground-truth incentive pointer
- **Question**: Should the ground-truth incentive pointer be re-targeted in this piece?
- **Resolution**: Yes. Re-point `GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER` in `python/analyze_issues.py` and the incentive pointer in `docs/ground-truth-verdict.md` from diagnostic-only #5461 to this incentive sub-issue #5544.
- **Source**: issue

## Decision 6: Hard guardrails (non-goals)
- **Question**: What must NOT change?
- **Resolution**: No panel weighting, no spawning/pruning changes, no token allocation (#4771 stays NO-GO), no re-exposure of proposer-controlled `body_severity`. Severity stays judge-set. Quorum/threshold semantics untouched. Keep the change surgical.
- **Source**: issue

## Decision 7: Cold-start / insufficient data
- **Question**: What happens when a tool has no/too-little recent calibration history?
- **Resolution**: Omit the calibration-feedback block entirely for that tool rather than inject misleading or empty stats. Underfilled window falls back to all-history; still-empty means no block. The voter prompt must render identically to today when no signal exists.
- **Source**: codebase / best-judgment

## Decision 8: Compute-once-per-run snapshot (performance)
- **Question**: Won't rolling up the last 100 run-log dirs per voter, per panel, per round slow runs down?
- **Resolution**: Yes, that repetition is avoidable waste. Compute the per-tool roll-up ONCE per run at the dispatch site (before launching voters), write a tiny snapshot file (3 rows: claude/codex/cursor) into the session tmpdir, and have each `render voter` read it via `--calibration-stats-file`. The 100-dir parse runs once per run, not once per voter. This also gives every voter in a run a consistent signal and resolves the issue's open "snapshot verb vs inline reads" question in favor of the snapshot. The kill-switch short-circuits snapshot computation entirely. Absolute inline cost is modest (a few seconds, dwarfed by LLM voting), but the snapshot removes the waste for near-zero marginal cost and bounds it against voters x rounds.
- **Source**: user concern + best-judgment
