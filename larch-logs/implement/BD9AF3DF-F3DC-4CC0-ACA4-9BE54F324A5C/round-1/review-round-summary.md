# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Final summary render lacks late `PUBLISH_OK` re-check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SUMMARY_OUTCOME` coercion consults `result_env_publish_ok_is_true` only once before `render-final-summary.sh`. A concurrent peer can write `PUBLISH_OK=true` after that check but before render, so the loser still renders `failed-publish` and overwrites an approved `final-summary.md` despite on-disk success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-check result_env_publish_ok_is_true immediately before render-final-summary.sh and coerce SUMMARY_OUTCOME=approved when late success is visible.
  - From cursor-specialist-edge-cases-output.txt: Re-check result_env_publish_ok_is_true immediately before render-final-summary.sh, or render after write_result_env_and_emit using post-write file state.
  - From codex-specialist-edge-cases-output.txt: Re-check result_env_publish_ok_is_true immediately before rendering failed-publish and coerce the outcome to approved when success is present.


### FINDING_3: Final-mode idempotent success gated on `REMOTE_BRANCH_EXISTS`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-log-branch-output.txt
- **Severity**: important
- **Concern**: Early final-mode idempotent success via default-branch `ls-tree` is skipped when `REMOTE_BRANCH_EXISTS` is true (including stale `refs/remotes/origin/larch-log-design-<RUN_ID>` after squash merge). Retries miss that logs are already on `origin/<default>`, attempt duplicate publish or fail, and return `PUBLISH_OK=false` instead of idempotent success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Run the origin/default ls-tree probe for all REASON=final invocations regardless of REMOTE_BRANCH_EXISTS.
  - From codex-specialist-correctness-output.txt: Use actual remote detection or clear stale refs, and run the final default-tree idempotency probe independent of remote branch detection.
  - From cursor-specialist-edge-cases-output.txt: Run default-branch ls-tree probe for all --reason final; do not tie idempotency to absence of remote log branch.
  - From codex-specialist-edge-cases-output.txt: Run the default-branch fetch and ls-tree probe for every REASON=final, and avoid treating stale remote-tracking refs as live remote branches.
  - From codex-specialist-testing-output.txt: Run the default-branch ls-tree probe for every REASON=final regardless of REMOTE_BRANCH_EXISTS, or verify/prune stale remote refs; add a stale-ref regression.
  - From dyn-log-branch-output.txt: Run the default-branch `ls-tree` idempotent probe for all `REASON=final` invocations (still after remote detection and before the concurrent-worktree guard), or at minimum probe when `REMOTE_BRANCH_EXISTS=true` and the default-branch tree already contains the run directory; keep pause fail-closed by leaving the block `REASON=final`-only.


### FINDING_7: Missing dual-invocation lock regression tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required dual-invocation result-env lock regressions (`success-first/failure-second`, `failure-first/success-second`) and metadata-preservation cases are absent. Seeded single-process simulations do not exercise real `mkdir` lock ordering; lock re-read and concurrent publish-tail races can regress while harnesses stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the planned dual-invocation lock tests and metadata-preservation regression.
  - From codex-specialist-correctness-output.txt: Add deterministic two-invocation lock tests for both orderings.
  - From cursor-specialist-testing-output.txt: Add success-first/failure-second and failure-first/success-second cases with two driver invocations on one tmpdir and assert final PUBLISH_OK=true when any publish-tail success was recorded.
  - From codex-specialist-testing-output.txt: Add deterministic concurrent publish-tail tests for success-first/failure-second and failure-first/success-second using stub barriers.


