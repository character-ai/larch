### FINDING_1: Divergent embedded gh stubs can mask harness regressions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-harness-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-log-publish.sh` and `scripts/test-design-multi-round-integration.sh` maintain separate `gh pr checks` stubs with different strictness, especially around `--json`, `--watch`, and `--fail-fast`, so one harness can pass while the other would catch an unsupported CLI shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-harness-fidelity-output.txt: Address the concern above.

### FINDING_2: Registration gate logic is inlined in a long script block
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The registration wait, headRefOid binding, and merge result assignment are embedded directly in `scripts/design-log-publish.sh`, making future edits harder to review and increasing duplication risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: `merge_rc` lacks a defensive initializer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `merge_rc` is used under `set -u`; current paths assign it, but a future refactor could trigger an unbound-variable abort instead of a clean `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Never-registered probe expectation is hardcoded
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The never-registered test hardcodes `31` probes without tying it to the production `REG_TIMEOUT` / `REG_INTERVAL` formula, making future timeout changes non-obvious.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Worktree cleanup precedes merge failure handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: On merge failure, the remote branch remains for recovery but local worktree state is already removed before the final `merge_rc` check; reviewers marked this as pre-existing recovery ergonomics, not a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Fixed registration budget may still false-fail on slow GitHub registration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A 300-second registration budget can still false-fail if GitHub is unusually slow to register checks; this was identified as an accepted trade-off rather than a new blocker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Pause recovery tests may not reach the intended merge-failure path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Several pause-recovery publish tests omit `TEST_CLONE_ROOT` / `TEST_MERGE_BRANCH`, so after headRefOid binding they can fail during registration instead of exercising `GH_STUB_MERGE_RC` merge-failure semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Success-path harnesses do not consistently assert registration probes before watch
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: Happy-path and stale-head-success tests can pass without proving `gh pr checks --json` registration probes occurred before `gh pr checks --watch --fail-fast`, so regressions that skip the completion watch could be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-fidelity-output.txt: Address the concern above.

### FINDING_9: Persistent `gh pr view` failure during registration is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness does not cover non-zero `gh pr view` during registration when checks JSON is non-empty, leaving the fail-closed registration-timeout behavior unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: PR head is not re-verified immediately before admin merge
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-gh-ci-gate-output.txt
- **Severity**: important
- **Concern**: `PUSH_HEAD_SHA` / `headRefOid` equality is checked to exit registration, but not rechecked after `--watch` and before `gh pr merge --admin`, leaving a window where a moved disposable branch could merge content not independently tied to the originally pushed SHA.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-gh-ci-gate-output.txt: Address the concern above.

### FINDING_11: Registration timeout message does not match actual wall-clock behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-contract-output.txt, dyn-gh-ci-gate-output.txt
- **Severity**: latent
- **Concern**: The registration loop is probe-count bounded while `gh pr view` retries can add backoff per probe, so elapsed wall time can exceed the advertised `${REG_TIMEOUT}s` diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-bash-contract-output.txt, dyn-gh-ci-gate-output.txt: Address the concern above.

### FINDING_12: Non-array gh JSON errors poll until timeout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Non-array JSON from `gh pr checks` is treated as “not registered,” causing auth/rate-limit/API-error responses to sleep and eventually surface as registration timeout rather than failing fast with a clear diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Stale-head coverage is not integrated with pause-reuse force-push flow
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-fidelity-output.txt
- **Severity**: important
- **Concern**: Stale-head behavior is covered by stub knobs but not by the pause-reuse / force-push fixture, so regressions in the combined recovery path could escape CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-fidelity-output.txt: Address the concern above.

### FINDING_14: Registration is not rechecked immediately before watch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Checks could disappear between the final successful registration probe and `gh pr checks --watch`, recreating a narrow no-checks-reported watch failure window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Post-push registration `mktemp` failures break recovery envelope
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: important
- **Concern**: If registration-phase `mktemp` fails after a successful push, the script emits `PUBLISH_OK=false` and exits `0` without `RECOVERY_BRANCH`, violating the documented post-push failure contract and hiding recovery information.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.

### FINDING_16: Registration temp files are not covered by cleanup trap
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: latent
- **Concern**: `reg_checks_err_file` and `reg_view_fail_file` are removed after the loop but not in `wt_cleanup`, so an early second-`mktemp` failure can leak the first temp file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] `design-publish.sh` may trust `PUBLISH_OK=true` despite non-zero publish exit
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: important
- **Concern**: If `design-log-publish.sh` exits non-zero while stdout contains `PUBLISH_OK=true`, failure branches may be skipped and rename may proceed; reviewer marked this as restored pre-existing envelope behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] No post-registration head recheck before watch or merge
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: latent
- **Concern**: After registration succeeds, the script relies on GitHub’s live PR-head behavior during watch/merge rather than independently rechecking `headRefOid`; reviewer treated this as reasonable for a bot-only branch and out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Completion watch remains unbounded
- **Reviewer(s)**: dyn-gh-ci-gate-output.txt
- **Severity**: latent
- **Concern**: `gh pr checks --watch` can hang indefinitely after registration succeeds if a required job never completes; reviewer marked this as pre-existing and orthogonal to the registration race fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-ci-gate-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Registration treats any non-empty JSON array as registered
- **Reviewer(s)**: dyn-gh-ci-gate-output.txt
- **Severity**: latent
- **Concern**: The registration predicate does not require specific pending/in-progress buckets, only a non-empty JSON array; reviewer noted this matches the plan but depends on `gh` representing required checks correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-ci-gate-output.txt: Address the concern above.

### FINDING_21: Probe counter can stay at one when `GH_STUB_LOG` is unset
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: JSON probe numbering only persists when `GH_STUB_LOG` or `GH_STUB_CHECKS_JSON_COUNT_FILE` is set, so pause-reuse paths without logs cannot validate multi-probe behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Removed sleep stub directories can cause slow later tests
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: Some cases remove tempdirs while `SLEEP_SCRIPT_DIR` may still point at a deleted no-op sleep stub, causing later multi-probe tests to fall back to real sleeps; reviewer marked this as mostly masked today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Duplicate gh stubs increase long-term drift
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: Separately embedded `gh` stubs across harnesses increase future drift risk; reviewer surfaced this as an out-of-scope architecture observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Publish envelope unit tests do not exercise merge gate
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-design-publish.sh` stubs `design-log-publish.sh` and therefore does not exercise the merge gate; reviewer considered this appropriate for that unit harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Address the concern above.

### FINDING_25: Publish tail drops PR and recovery envelope fields
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` parses and persists only part of the `design-log-publish.sh` envelope, omitting `PR_NUMBER`, `PR_URL`, and `RECOVERY_BRANCH`; this hides successful flush PR details in final summaries and hides recovery pointers on publish failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Post-publish render runs before issue rename
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: latent
- **Concern**: Post-publish rendering and tracking-issue summary upsert run before `[DESIGNED]` rename; reviewer marked this ordering as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Post-publish render keeps approved outcome when publish fails
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: nit
- **Concern**: The post-publish render uses `--outcome approved` even when `PUBLISH_OK=false`; reviewer treated this as matching the documented Gate-C vs log-flush split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Address the concern above.
