### FINDING_2: Retire the agentic-fix call path cleanly
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-dyn-Ci Fixer Orchestrator
- **Severity**: major
- **Concern**: `evaluate_failure()` still reaches the deleted `agentic-fix` helper when rebase is not pending, so removing the registry entry alone leaves a dead call site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `ci_monitor.py` UPDATED scope, replace the non-pending branch with immediate main-agent handoff semantics (no subprocess fixer), delete `_agentic_fix_result` and its argv/timeout helpers, and rewrite tests to assert bail/handoff instead of agentic delegate success
  - From Codex-Arch: Add a plan step to rewrite that branch to the new file-backed distill-log plus Agent-tool spawn, or keep a compatibility shim until every caller is moved.
  - From Cursor-Pragmatic: Specify evaluate_failure non-pending path returns immediate main-agent handoff (mirror monitor first-fixer-non-health) or delete/simplify function; update tests accordingly
  - From Cursor-dyn-Ci Fixer Orchestrator: Replace that branch with immediate main-agent handoff (no Python-side fixer); keep only the ci_fix_rebase_pending retry path; update test_ci_monitor.py evaluate_failure tests accordingly.


### FINDING_5: Remove surviving agentic-fix tests with the code
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The old CLI/helper is being deleted, but test coverage still references it, so the suite will stay red unless the surviving tests are rewritten in the same change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Remove or replace the `test_agentic_fix_*` block in test_ci.py in the same change set as deleting `ci agentic-fix`
  - From Codex-Arch: Extend the test cleanup in the plan to remove or rewrite these cases to the new ci distill-log and ship-pr ci-fix flow.
  - From Cursor-Pragmatic: List test_ci.py cleanup: remove agentic_fix tests when registry entry is removed


### FINDING_6: Retarget harness needles for rewritten prose
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Ci Fixer Orchestrator
- **Severity**: major
- **Concern**: Rewording the reference prose will break exact-string harness checks unless the updated needles are listed alongside the rewrite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Promote the harness to UPDATED and list pinned strings that must remain (or update `EXPECTED_*` literals) alongside the ship-pr-ci-fix.md rewrite
  - From Cursor-Innovation: Add ### UPDATED: scripts/test-implement-structure.sh and ### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh with explicit needle retargeting for the fixer/default path, kill switch, and retained inline fallback contracts
  - From Cursor-dyn-Ci Fixer Orchestrator: Add ### UPDATED entries for both harness scripts; retarget pins to fixer-spawned.sentinel, fixer-bail.md, 10-attempt fallback, and no main-agent gh run-logs on the fixer-default path; run them in Testing strategy.


### FINDING_7: Keep the 30-round budget and kill switch semantics separate
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Ci Fixer Orchestrator
- **Severity**: major
- **Concern**: The plan lowers the required fixer budget and folds the kill-switch path into the new fallback path, so it no longer matches the current 30-round fixer contract or the intended inline baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Split the kill-switch path from the post-bail fallback. Keep the existing 30-attempt inline procedure for LARCH_CI_FIXER=0 and reserve the 10-attempt cap for fixer-bail recovery only
  - From Cursor-Pragmatic: Either update issue acceptance to Round 1 20/10 split counters or restore 30-round fixer budget and shared counter semantics from ship-pr-ci-fix step 3
  - From Cursor-Requirements: Change the fixer budget, prompt prose, config constant, and tests from 20 to 30 rounds; keep any separate main-agent fallback cap only after the 30 fixer rounds
  - From Cursor-dyn-Ci Fixer Orchestrator: Use the existing per-run-id CI-fix counter/sentinel or an extension of it as the single attempt surface; set the fixer loop cap to 30; let main-agent fallback start only after fixer exhaustion or explicit bail without reducing the fixer's required rounds.
  - From Cursor-dyn-Ci Fixer Orchestrator: State that after 10 main-agent inline attempts the procedure ends and routes operator-bail (ci-fix-exhausted); do not respawn the fixer.


### FINDING_9: Make the run-id handoff state durable
- **Reviewer(s)**: Cursor-dyn-Ci Fixer Orchestrator, Codex-dyn-Ci Fixer Orchestrator
- **Severity**: major
- **Concern**: The one-spawn guard and the fallback attempt surface are not durable enough to survive re-entry, so a repeated `ci-fix` episode could respawn the fixer or reset the inline fallback count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Ci Fixer Orchestrator: In ship-pr-ci-fix.md require: write fixer-spawned.sentinel before Agent dispatch; treat fixer-spawned.sentinel OR fixer-bail.md for that run id as a hard no-spawn guard; on success still block respawn for the same run id.
  - From Codex-dyn-Ci Fixer Orchestrator: Make `fixer-spawned.sentinel` mandatory, write it before Agent dispatch, and refuse to spawn when it already exists.
  - From Codex-dyn-Ci Fixer Orchestrator: Store the fallback attempt count under `$IMPLEMENT_TMPDIR/ci-fixer-$FAILED_RUN_ID/` and update it before each inline attempt, or explicitly extend the existing per-run-id counter surface.


### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: [SCOPE-REDUCTION] Missing pre-spawn distill-log fence before Agent spawn. Scenario: Fixer inputs require distilled-failure.md but the plan never states that the main agent runs python/cli.py ci distill-log (stdout KVs only, no Read of the digest) before spawning; orchestrators may spawn with a missing digest or read logs into main context on the success path
- **Proposed resolution**: Add a numbered precondition: write $IMPLEMENT_TMPDIR/ci-fixer-$FAILED_RUN_ID/distilled-failure.md via ci distill-log, parse STATUS KVs only, then write fixer-spawned.sentinel and spawn once


### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/implement/references/ship-pr-ci-fix.md:15-15
- **Concern**: [SCOPE-REDUCTION] Fixer budget diverges from issue acceptance without reconciliation. Scenario: Binding issue scope and acceptance criteria require a 30-round fixer cap and shared attempt surface; Round 1 binds 20 fixer rounds plus 10 inline attempts on separate counters, so shipped behavior will not meet written acceptance unless the issue is updated
- **Proposed resolution**: Reconcile issue acceptance/title with 20+10 (or restore 30 fixer rounds) and state whether fixer rounds and main-agent attempts share one counter surface per the original requirement


### FINDING_2: Distill log must not tail-truncate failures
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The distill-log path appears to rely on tail-only CI log collection, which can omit failures from multi-job runs and leave the fixer with incomplete evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement distill_log_main against gh run view --log-failed with per-job section parsing head/tail caps and shard dedupe; forbid delegating to collect_failed_logs or other repo-wide tail truncation helpers


### FINDING_6: Stale CI_AGENTIC_FIX_MAX_CYCLES assertions after config cleanup
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The config cleanup will break existing tests unless the stale CI_AGENTIC_FIX_MAX_CYCLES assertions and monkeypatches are removed or rewritten alongside the symbol deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: The plan removes `CI_AGENTIC_FIX_MAX_CYCLES`, but this test still asserts it, and `python/tests/implement/test_ci_monitor.py:3325-3334` still monkeypatches it. The suite will go red as soon as config.py drops the symbol. Replace those checks with the new `CI_FIXER_*` constants or delete the affected tests in the same change set.


