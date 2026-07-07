# Accepted plan-review findings audit (Gate C)

## Strong-disagree
- FINDING_7 (r1, major — "Keep the 30-round budget and kill switch semantics separate"): the accepted finding's "restore 30 fixer rounds" application contradicts binding Round 1 Decision 2 in discussion-round1.md (fixer sub-agent = 20 rounds). Final plan keeps the fixer at 20 (Round 1 authority) and preserves the finding's valid structural half: kill-switch inline and post-bail fallback are separate paths, kill-switch restores today's 30-attempt behavior, post-bail = 10. Strong per the escalation bar (an accepted finding whose application contradicts an explicit Round 1 decision). Pre-review baseline (plan-before-review.txt) was already 20; the loop's 30 was a transient regression now reverted.

## Agree (applied faithfully; no Round 1 conflict)
- FINDING_2 (r1): retire the agentic-fix call path cleanly — applied (evaluate_failure non-pending immediate handoff; delete _agentic_fix_result and siblings).
- FINDING_5 (r1): remove surviving agentic-fix tests — applied (test_ci.py cleanup in same change set).
- FINDING_6 (r1): retarget harness needles — applied (test-implement-structure.sh, test-implement-step8-exit3-first-fixer.sh).
- FINDING_9 (r1): durable run-id handoff — applied (fixer-spawned.sentinel before dispatch; no-spawn guard; durable fallback-attempts.count).
- FINDING_11 (r1, [SCOPE-REDUCTION]): pre-spawn distill-log fence — applied (Approach step 5).
- FINDING_13 (r1, [SCOPE-REDUCTION]): reconcile fixer budget vs issue acceptance — reconciled toward Round 1 20+10 with an explicit note that the larch:plan block supersedes the issue's "30 rounds" text.
- FINDING_2 (r2): distill-log must not tail-truncate — applied (gh run view --log-failed per-job parsing; forbid collect_failed_logs delegation).
- FINDING_6 (r2): stale CI_AGENTIC_FIX_MAX_CYCLES assertions — applied (test_config.py + test_ci_monitor.py delegate-timeout cleanup).

## Fidelity
- Every final-plan change traces to an accepted finding, a postplan validation fix, or the binding Round 1 decision. The only deliberate divergence from an accepted finding is FINDING_7's 30-round value, reverted to 20 per Round 1 (recorded above). No one-by-one operator skips (auto-apply mode).
