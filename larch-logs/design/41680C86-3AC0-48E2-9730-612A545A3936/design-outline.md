## Proposed Design Outline

### Goals
- Inject each voter tool's recent calibration (High Rate / Calibration Score) into its voter prompt so calibrated severity tagging becomes dominant and panel High Rate falls (issue #5544, Option A).
- Cover both code-review and plan-review voter dispatch paths.

### Non-goals
- No panel weighting, spawning/pruning, or token allocation (#4771 stays NO-GO).
- No proposer-controlled `body_severity` re-exposure; severity stays judge-set.
- No quorum/threshold/eligibility changes.

### Approach sketch
- New per-tool roll-up reader in `python/voting.py`: last 100 run-log dirs by recency, fall back to all-history; reuse `compute_voter_severity_distribution` / `severity_calibration_score`.
- Compute the per-tool snapshot ONCE per run at each dispatch site; write a tiny stats file into the session tmpdir (avoids re-parsing 100 logs per voter).
- `render voter` gains optional `--calibration-stats-file`; injects a tool-keyed feedback block after the severity rubric; omits it when no data (cold-start safe).
- Default ON with env kill-switch; window env-tunable (default 100); define both env vars in `config.py` (G-Cfg-1).
- Re-point the ground-truth incentive pointer to #5544.

### Surfaces in scope
- `python/voting.py`, `python/rendering.py`, `python/agent_voters.py`, `python/plan_review_panel.py`, `python/cli.py` (snapshot verb), `python/config.py` (env Finals).
- `python/analyze_issues.py`, `docs/ground-truth-verdict.md` (incentive pointer to #5544).
- Tests: `python/test_voting.py`, `python/test_rendering.py`, `python/test_agent_voters.py`, `python/test_plan_review.py`.

### Open questions
- None.
