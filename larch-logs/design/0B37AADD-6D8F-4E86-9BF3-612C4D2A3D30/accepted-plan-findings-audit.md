# Gate C accepted-findings audit

Classification: 1 strong-disagree, remainder agree. STRONG_AUDIT_DISSENT=true.

## Strong-disagree

### FINDING_8 (round 1, [SCOPE-REDUCTION]) — resume/compact reset resolution
- Sections: Approach 4; `python/larch/report/statusline.py`; `python/tests/report/test_progress_statusline.py`; `docs/progress-reporting.md`.
- Applied resolution: keep `resume`/`compact` OUT of `RESET_SESSION_SOURCES` (no-op reset sources).
- Divergence: reverses explicit Round 1 Decision 3 ("add resume/compact reset, scoped") and the approved-outline approach item ("add resume/compact to RESET_SESSION_SOURCES and scope the reset veto"). Pre-review plan added them; review removed them.
- Why the finding is valid: a naive resume/compact reset with bgjob-only preservation would clear active foreground runs (early steps write via `append_breadcrumb`, which no-ops without `current`).
- Unaddressed middle-ground: the finding itself offered option (b): gate reset on an active in-progress signal (live tmpdir / fresh breadcrumb mtime) not only bgjob liveness. Option (b) honors Decision 3 and avoids the foreground-silencing regression. The plan took option (a) instead.
- Residual: a run that skips every deactivation path (hard crash) still renders stale on immediate `--continue`/`--resume`; it self-heals only on the next fresh startup. Narrow, but contrary to Decision 3's stated goal.
- Recommendation: operator decides. Accept option (a) as-is (simpler, reported symptoms already fixed by comprehensive deactivation), or Discuss further / Re-run review to adopt option (b).

## Agree (applied, consistent with goals and hard constraints)
- Run-id correlation: persist `LARCH_RUN_ID` through session env; align registry run-id validation; propagate to every `registry.read_for` caller (round 1 FINDING_1; round 2 FINDING_1/2/3). Applies I-Stale-1.
- Terminal coverage: deactivate on Step 0 abort and all terminal/cancel exits, including after failed staging (round 1 FINDING_2/5; round 2 FINDING_8).
- Reviewer-probe ordering pinned so degraded-tools routing is preserved (round 1 FINDING_3).
- Compare-and-clear run-matched under a clone-local lock; serialize activate/deactivate (round 1 FINDING_7; round 2 FINDING_7).
- Fidelity: each final-plan change traces to an accepted finding or the original scope; no unexplained additions.
