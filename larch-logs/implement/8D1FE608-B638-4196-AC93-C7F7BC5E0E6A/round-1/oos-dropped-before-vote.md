### OOS_1: [OUT_OF_SCOPE] Poll interval bounds policy-rejection detection latency
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-lintfix-prompt
- **Severity**: latent
- **Concern**: Production fast-fail latency is bounded by `RUN_EXTERNAL_AGENT_POLL_INTERVAL` (default 10 s), not the 0.05 s used in tests. Rejection visible in events or sidecar may not be acted on for up to one poll interval. This is a large improvement over 300 s, but not immediate detection on the first event byte.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Lower poll interval for Codex exec or scan events on a shorter sub-interval (optional polish).

### OOS_2: [OUT_OF_SCOPE] Fast-fail negative test matrix half-covered
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Fast-fail negative coverage only omits the `exec_command failed` family (policy tokens without `exec_command failed`). The inverse case (`exec_command failed` without policy tokens) is untested. Low risk given the AND detector, but it is only half of the "single-family" matrix the plan described.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] No test for partial event writes across poll intervals
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: No test exercises incremental tail assembly across multiple poll intervals when rejection evidence arrives in separate writes (plan edge case: "Partial event writes"). Typical production failures emit both families in one line; an offset-tracking regression could delay fast-fail until timeout.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] No integration test for run_lint_fix site threading into Codex appendix
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: No integration test asserts `run_lint_fix(site="step5-review-fixes")` threads that machine site into the Codex `prompt.md` appendix. The reported bug was site-label mismatch; `_run_codex` unit tests cover appendix binding, and `run_lint_fix` is a one-line `site=site` pass-through, so regression risk is low but the exact failure mode is not re-tested end-to-end.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Lint-fix harness lacks site-split pair coverage
- **Reviewer(s)**: dyn-dyn-lintfix-prompt
- **Severity**: latent
- **Concern**: The lint-fix harness exercises `step3` where lint and capture sites are the same, but does not cover the Step 5 (`step5-mav` / `step5-review-fixes`) or ship-pr (`ship-pr-ci-initial` / `step6`) site-split pairs. A combined-prompt assertion for those pairs would catch appendix/capture drift earlier.
- **Suggested revisions (informational for voters; coder decides)**:
