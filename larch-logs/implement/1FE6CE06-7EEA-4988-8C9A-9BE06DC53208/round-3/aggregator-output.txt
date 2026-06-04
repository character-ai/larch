### FINDING_1: Registration timeout can exceed advertised wall-clock budget
- **Reviewer(s)**: dyn-poll-loop-state-output.txt
- **Severity**: important
- **Concern**: The registration loop bounds the number of polling sleeps but not total elapsed time, so transient retry backoffs inside each probe can make a nominal 300s timeout run much longer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-poll-loop-state-output.txt: Either (a) use a wall-clock deadline (`deadline=$((SECONDS + REG_TIMEOUT))` and stop probing when `SECONDS >= deadline`, counting all sleeps including `with_transient_retry`), (b) drop `with_transient_retry` inside the registration loop and rely on the outer poll cadence for transient `pr view` errors, or (c) cap registration `pr view` to a single attempt per probe and document that `REG_TIMEOUT` is sleep-budget-only.

### FINDING_2: [OUT_OF_SCOPE] merge_rc appears assigned on all reachable registration-loop exits
- **Reviewer(s)**: dyn-poll-loop-state-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed no reachable branch where `merge_rc` remains unset before it is tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-poll-loop-state-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Final registration probe does not sleep afterward
- **Reviewer(s)**: dyn-poll-loop-state-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that sleep placement matches the plan because the final probe does not perform a trailing sleep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-poll-loop-state-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Missing jq or unparseable checks JSON fails closed through timeout
- **Reviewer(s)**: dyn-poll-loop-state-output.txt
- **Severity**: nit
- **Concern**: If `jq` is missing or captured JSON is empty/unparseable, registration is treated as not yet complete and eventually fails closed through the registration-timeout path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-poll-loop-state-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Registration does not prove individual check runs belong to pushed SHA
- **Reviewer(s)**: dyn-poll-loop-state-output.txt
- **Severity**: latent
- **Concern**: Registration verifies non-empty required-check JSON and matching `headRefOid`, but does not directly assert each check run belongs to `PUSH_HEAD_SHA`, leaving a theoretical force-push race to monitor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-poll-loop-state-output.txt: Address the concern above.

### FINDING_6: Unplanned plan-review-loop and multi-round integration changes reduce traceability and leave stderr buffering behavior under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop.sh` and `test-design-multi-round-integration.sh` changed outside the plan’s affected-files list. The stderr-forwarding change also changes streaming behavior to buffered replay without a dedicated regression assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: add `skills/design/scripts/plan-review-loop.sh` (and its sibling `.md`) to the plan's files list with a one-line rationale ("process-substitution stderr forwarding caused timing issues in the integration test"), or squash the change into a separate labelled commit so it is discoverable from `git log`.
  - From cursor-specialist-testing-output.txt: add a test assertion (or a comment in the harness) confirming stderr propagation reaches the collector error file after a non-zero collector exit, and add the file to the plan's affected-files list / `relevant-checks.sh` scope to prevent silent regression.
  - From cursor-specialist-plan-fidelity-output.txt: Record this as a separate incidental fix in the plan (or in the PR description); its absence from the plan makes it invisible to completeness reviewers.
  - From cursor-specialist-plan-fidelity-output.txt: Add this file to the plan's file list with a note that the stub update is required to keep the integration test passing under the new gate protocol.

### FINDING_7: reg_checks_rc is intentionally unused but only acknowledged by a no-op
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `reg_checks_rc` is captured but not semantically used; without an explanatory comment, future maintainers may incorrectly treat the `gh pr checks` exit code as the registration signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Replace `: "$reg_checks_rc"` with a `# shellcheck disable=SC2034` comment, or simply remove the captured rc assignment and the no-op.
  - From cursor-specialist-security-output.txt: Add a one-line comment immediately after the assignment: `# rc intentionally unused; JSON array content — not gh's exit code — is the registration signal (see #3413)`.

### FINDING_8: Publish failure-envelope tests under-assert failed-publish outcome
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Two `test-design-publish.sh` failure-envelope cases assert that `post-publish-only` rendered, but do not assert `--outcome failed-publish`, unlike the analogous `PUBLISH_OK=false` case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add `grep -q -- '--outcome failed-publish' "$RENDER_LOG" || fail "unexpected publish rc should render failed-publish outcome"` after the existing `post-publish-only` assertion in the nonzero-without-KV block. Same gap exists in the exit-0-no-KV block.
  - From cursor-specialist-testing-output.txt: add `grep -q -- '--outcome failed-publish' "$RENDER_LOG"` assertions to both the unexpected-rc and the exit-0-no-KV test blocks.

### FINDING_9: Deleted sleep stubs can leak through later test blocks
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Some `test-design-log-publish.sh` cases leave `SLEEP_SCRIPT_DIR` pointing at a deleted temp sleep stub, so future test edits could unexpectedly fall back to real `sleep`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: add `export SLEEP_SCRIPT_DIR="$GLOBAL_SLEEP_STUB"` at the start of the nonzero-rc case, matching the reset pattern already used in the registration-view-failure and stale-head-never-aligns cases.
  - From cursor-specialist-edge-cases-output.txt: add `export SLEEP_SCRIPT_DIR="$GLOBAL_SLEEP_STUB"` before `rm -rf "$TMPSTALE"` on line 1057, matching the pattern used by the `=== registration pr view failure refuses merge ===` and `=== stale head never aligns ===` blocks.

### FINDING_10: GH_STUB_PR_VIEW_RC affects all pr view shapes instead of only headRefOid probes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `pr view` stub’s `GH_STUB_PR_VIEW_RC` short-circuit fires before dispatching on requested JSON fields, so a headRefOid failure knob can also break URL lookup calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: guard `GH_STUB_PR_VIEW_RC` only when the call includes `--json headRefOid` (or move it into the `headRefOid` case arm), and add a dedicated `GH_STUB_PR_VIEW_HEAD_RC` knob for that slot.

### FINDING_11: Parseable non-array checks JSON aborts registration immediately instead of retrying
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: A transient GitHub response such as a rate-limit JSON object causes `checks_registration_fatal=true` and exits the registration loop after one probe, rather than using the remaining poll budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Replace the fatal break with a continue (treat non-array JSON as "not registered yet") or add a bounded retry counter for non-array cases before switching to fatal, consistent with the transient-network-error resilience documented in the plan's failure-modes section.
  - From cursor-specialist-plan-fidelity-output.txt: Either treat parseable non-array JSON as "not registered, keep polling" (matching the plan's implied behaviour), or add the rate-limit/transient-object case to the plan's failure-modes with a rationale for immediate failure.

### FINDING_12: [OUT_OF_SCOPE] plan-review-loop mktemp failure lacks fallback
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The explicit temp-file stderr approach exposes pre-existing fragility where `mktemp` failure could leave stderr capture broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add || fail/larch_err on the mktemp call; pre-existing issue outside this diff's scope

### FINDING_13: reg_view_fail_file may accumulate stale diagnostics across registration probes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The registration loop reuses `reg_view_fail_file` without clearing it before each `with_transient_retry`, so stale transient errors may appear in the final timeout diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: add `: >"$reg_view_fail_file"` immediately before the `with_transient_retry` call at line 844, mirroring the `reg_checks_err_file` pattern on line 826.

### FINDING_14: Stub override counters can collapse total-probe and knob-probe state into one file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When count-file override env vars are set, total probe counters and knob counters can resolve to the same file, corrupting threshold behavior for checks JSON and headRefOid stubs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: use a separate hard-coded suffix for the knob counter that ignores the override, e.g. `"${GH_STUB_LOG:-/tmp/gh-stub}.checks-json-knob-count"` unconditionally, so it cannot collapse with the total-count file.

### FINDING_15: failed-publish renderer changes and DESIGN_LOG_* interface are unplanned
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The diff modifies renderer-related files and adds a `failed-publish` outcome plus `DESIGN_LOG_*` env interface, but the plan did not list those files or requirements; related tests may therefore be either necessary but unplanned or over-constraining depending on whether the new outcome is formalized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add `skills/design/SKILL.md`, `skills/design/scripts/render-final-summary.sh`, `skills/design/scripts/render-final-summary.md`, and `skills/design/scripts/test-render-final-summary.sh` to the plan's "Files to modify/create" section with the `failed-publish` outcome requirements, and document the new `DESIGN_LOG_*` env-var interface between `design-publish.sh` and `render-final-summary.sh`.
  - From cursor-specialist-plan-fidelity-output.txt: If `failed-publish` is formally added to the plan, the assertion is correct; if not, relax the assertion to check only that `post-publish-only` is called.

### FINDING_16: PUBLISH_OK=false with rc 0 records a publish failure as exit code 0
- **Reviewer(s)**: dyn-caller-exit-contract-output.txt
- **Severity**: latent
- **Concern**: A reachable `PUBLISH_OK=false` / `_publish_rc=0` path can cause `execution-issues.md` to record a publish failure with exit code 0, obscuring an actual pre-push failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-exit-contract-output.txt: In the `elif PUBLISH_OK==false` arm, use `--exit-code "${_publish_rc:-1}"` → `--exit-code "${_publish_rc:-0}"` only for the zero-exit-expected case, or defensively use `1` as the floor: `--exit-code "$(( _publish_rc == 0 ? 1 : _publish_rc ))"` so failure logs always carry a non-zero exit code that `append-tool-failure.sh` will surface as an actual failure; the pre-existing `_publish_rc -ne 0` first branch already uses the raw rc directly.

### FINDING_17: LOG_RECOVERY_BRANCH is redundant and may mislead future consumers
- **Reviewer(s)**: dyn-caller-exit-contract-output.txt
- **Severity**: latent
- **Concern**: `LOG_RECOVERY_BRANCH` is synthesized to equal `RECOVERY_BRANCH` and is not read by the live renderer path, creating ambiguity for future consumers that might expect a distinct meaning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-exit-contract-output.txt: Either document in `design-publish.md` that `LOG_RECOVERY_BRANCH` is always identical to `RECOVERY_BRANCH` and exists for legacy compatibility, or drop the redundant key since no current consumer reads it and the exported env var `DESIGN_LOG_RECOVERY_BRANCH` already covers the one live use.

### FINDING_18: [OUT_OF_SCOPE] Registration jq predicate is split into two processes
- **Reviewer(s)**: dyn-caller-exit-contract-output.txt
- **Severity**: nit
- **Concern**: The registration loop parses the same captured JSON twice with separate `jq` predicates instead of using the single combined predicate described by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-exit-contract-output.txt: Address the concern above.
