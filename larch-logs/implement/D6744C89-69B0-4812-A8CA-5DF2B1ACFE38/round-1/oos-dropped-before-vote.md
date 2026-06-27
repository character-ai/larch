### OOS_1: [OUT_OF_SCOPE] Harness does not verify hooks.json registration
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The harness does not verify that `hooks.json` registers the hook on `Stop` and `UserPromptSubmit`. Removing `hooks.json` entries would disable the circuit breaker in production while `make test-hook-no-progress-guard` still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add jq registration assertions like test-hook-bg-poll-guard.sh and test-hook-progress-report.sh.

### OOS_2: [OUT_OF_SCOPE] find maxdepth 2 under sessions misses nested markers
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `find` with `maxdepth 2` under sessions misses nested markers; copied from `hook-bg-poll-guard`. Discovery fails if `TMPDIR` is not a session dir. Pre-existing; shared discovery fix.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Multiple Stop hooks; unclear short-circuit behavior
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Multiple `Stop` hooks are registered; unclear if all run when the first blocks. Counting may be skipped if the platform short-circuits `Stop` hooks. Pre-existing pattern.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] orchestrator-never.md NEVER #5 overstates auto-disarm
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: NEVER #5 overstates auto-disarm vs file persistence. Misleading operator expectations. Align prose with actual reset behavior.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] SECURITY.md does not document hook-no-progress-guard
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `SECURITY.md` does not document `hook-no-progress-guard.sh` `UserPromptSubmit` blocking. Operators miss the circuit breaker when auditing hook policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a SECURITY.md subsection for the new hook.

### OOS_6: [OUT_OF_SCOPE] No OOS harness test for stale armed state across sequential waits
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: No test for stale armed state across sequential waits in one tmpdir. Regression from stale-state bugs could reappear silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add T11 sequential-wait stale-state test.

### OOS_7: [OUT_OF_SCOPE] implement SKILL.md omits no-progress guard backstop
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Implement SKILL still documents only bg-poll-guard for background waits. Implement orchestrators may not know about `Stop`/`UserPromptSubmit` backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Cross-reference orchestrator-never #5 or design-background-wait breaker paragraph.

### OOS_8: [OUT_OF_SCOPE] is_marker_live omits is_allowed_marker_parent (low practical risk)
- **Reviewer(s)**: dyn-dyn-hook-correctness
- **Severity**: latent
- **Concern**: `is_marker_live` omits `is_allowed_marker_parent` from `hook-bg-poll-guard.sh`. A crafted `.bg-wait-active` under a broad `find` path could participate in counting/blocking if `CLAUDE_PID` matches. Low practical risk because legitimate markers live in session tmpdirs; aligning parent-dir validation would close the gap.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] counter_bump concurrency can lose increments (fail-open)
- **Reviewer(s)**: dyn-dyn-hook-correctness
- **Severity**: latent
- **Concern**: `counter_bump` uses the same best-effort `tmp.$$` + `mv` pattern as `probe_counter_bump` in `hook-bg-poll-guard.sh`. Concurrent hook processes can lose increments (fail-open: weaker protection, not false blocks). Acceptable given the documented fail-open posture; no change required unless true atomicity is needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-correctness: no change required unless true atomicity is needed

### OOS_10: [OUT_OF_SCOPE] Stop counts every turn under live marker (intentional K-turn budget)
- **Reviewer(s)**: dyn-dyn-hook-correctness
- **Severity**: latent
- **Concern**: The `Stop` handler counts every turn end under a live marker, not only prose-only no-progress turns. That matches the stated K-turn budget, but five legitimate recovery turns that each end with a sanctioned foreground probe will arm the breaker before a long background job finishes. Threshold tuning or progress-aware reset would reduce false positives; behavior is intentional today but worth monitoring in production `/design` Step 3 waits.
- **Suggested revisions (informational for voters; coder decides)**:

