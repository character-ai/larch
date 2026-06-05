### OOS_1: [OUT_OF_SCOPE] TierAttempt 0,0 exit codes with LaunchFailure may break if waterfall semantics change
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Vendor push tests use `TierAttempt(tier, 0, 0, LaunchFailure(...))` to force a winning tier without a real agent. If `run_waterfall` starts treating `LaunchFailure` as tier failure regardless of exit codes, these tests may fail before reaching push. Pre-existing pattern; only refactor if waterfall semantics change (not required for #3405).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Empty-delta and failed-push share detail="push failed"
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-test-fixture-integrity-output.txt
- **Severity**: latent
- **Concern**: `run_ci_fix` at python/ci_monitor.py:1014-1023 reports `detail="push failed"` whenever `stage_and_push` returns `pushed=False`, including the empty-delta shortcut that never runs `git push`. Retry with no delta still reports push failed though no push ran. Predates this branch; the new test’s outer retries rely on that wording but do not hit the push stub on attempts 2–3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split detail for empty delta vs push failure in a follow-up if operators need clearer diagnostics.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] No rollback on push failure (pre-existing; Phase 7)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing behavior: push failure does not roll back, so Phase 7 wiring may surface inconsistent local state during CI fix recovery. Not changed by this PR’s documentation focus; track on Phase 7 cutover, not here.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Bash CI_FIX_REBASE_PENDING push-only retry not ported by design
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh:1618-1718` persisted push-only retry under `CI_FIX_REBASE_PENDING` is intentionally not ported to Python until `LARCH_SHIP_PR_IMPL=python`. Live implement path still uses bash; tracked via #3405 with no action on this PR.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (brief):** Input findings 1, 5, 9, and 12 describe the same test-fixture / assertion gap around outer retries and ambiguous `STALLED` + `push failed` detail. Findings 6 and 13 are the same production diagnostic quirk (OOS). In-scope comment request (input 7) stays separate from OOS no-rollback / bash-port items (input 10, 11). Input 8 stays separate from FINDING_1 because it targets rev-parse/HEAD semantics, not push-call counting or detail strings.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

