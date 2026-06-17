### OOS_1: [OUT_OF_SCOPE] Upfront transient blind-rerun can skip pending force-push
- **Reviewer(s)**: dyn-ci-monitor-trim-output.txt
- **Severity**: latent
- **Concern**: Upfront transient blind-rerun runs before the `ci_fix_rebase_pending` branch in `python/ci_monitor.py:1465-1498`, so a pending rebase retry can return `no-changes` and skip `run_ci_fix` force-push. Predates this trim; the branch does not add a guard.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_2: [OUT_OF_SCOPE] Parent timeout after push maps checkpoint to pushed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-conflict-guard-output.txt, dyn-ci-monitor-trim-output.txt
- **Severity**: latent
- **Concern**: On delegate subprocess timeout after a successful push, `_agentic_fix_result` in `python/ci_monitor.py:1378-1399` can still reconstruct `status="pushed"` from a push checkpoint when CI wait outcome is unknown. The parent may treat unknown post-push CI state as progress. Reviewers mark this as pre-existing and outside this PR's scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Consider aligning timeout recovery with wait fail-closed semantics in a follow-up.
  - From cursor-specialist-edge-cases-output.txt: On timeout with a push checkpoint and no completed wait, return fix-exhausted or require rebase-pending before promoting to pushed.


### OOS_3: [OUT_OF_SCOPE] Parent timeout recovery maps ci-wait errors to pushed (in-scope variant)
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Parent timeout recovery still maps ci-wait error checkpoints to `pushed`. A delegate can write `DETAIL=ci-wait-malformed-output` in `python/ci_agentic_fix.py:393-402`, then time out before emitting stdout; the parent returns `pushed` and can continue on stale CI state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Record terminal status in the checkpoint, or map ci-wait error details to fix-exhausted in `_agentic_fix_result`.


