# Review Round 1

- Mode: `diff`
- 4 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_1: correctness: python/ship.py:1428-1510
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Completeness w.r.t. plan: cold resume seeds last_monitored_head to current HEAD so first monitor call gets grace 0 after a prior head-changing push. Operator stops hung ship and reruns Step 8+ with PR head already at CI-fix commit and 0 checks; first monitor poll uses grace 0 and can hang for full CI_WAIT_TIMEOUT_SEC again. Seed last_monitored_head from CI_FIX_REBASE_PENDING_HEAD or stored prior head on resume, or apply post-push grace when fix_attempts increased or CI_FIX_REBASE_PENDING is set.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: python/ship.py:1428,1505-1510
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Bounded no-checks detection is process-local because last_monitored_head is initialized to the current post-resume HEAD. After a CI-fix push creates h1 with zero checks, killing or restarting the ship driver before the next loop seeds last_monitored_head=h1, post_push_grace remains 0, and the resumed monitor polls pending for the full 180 x 10s budget. Persist a post-push startup-check-needed head or previous monitored head in ship-pr-state.sh, and use CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC on resume when that pushed head still needs a fresh CI-run check.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: python/ship.py:1428-1510
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-push detection is process-local and is lost on resume. If the task is stopped after a CI-fix or rebase push, resume seeds last_monitored_head to the pushed SHA, passes grace 0, and can hang on zero checks again. Persist a fresh-CI-required marker or previous monitored head in ship-pr-state.sh and consume it on resume.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: python/ship.py:1428-1510
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [latent] Post-push empty-check detection is process-local and is lost on resume. If the driver stops after a CI-fix push and resumes from PHASE=ci-initial with zero checks, last_monitored_head is seeded to the already-pushed HEAD and empty_checks_grace remains 0, so the 30-minute pending poll can recur. Persist a fresh-CI-expected head marker in ship-pr-state.sh, consume it on resume with CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC, and add a resume regression test.
- **Suggested revision**: Address the concern above.


