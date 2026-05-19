### FINDING_11: correctness: scripts/test-launch-review.sh:954-1001
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] SL-transient-obs-nontransient contradicts implementation plan assertion (c) and the case comment: plan and comment require no transient-retries substring; test requires grep match on transient-retries=1. Operators or reviewers following the plan or the adjacent test comment conclude the log must omit transient-retries=, but CI enforces the opposite; the branch is self-inconsistent as written. Align plan bullet (c), the case comment, and assertions with one contract (either omit transient-retries= on this path or document and assert transient-retries=1 everywhere).
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/launch-review.sh:958 and scripts/test-launch-review.sh cursor subshell
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cursor path receives TRANSIENT_ATTEMPT in append_launch_failure but new observability tests run only under the codex suite. Cursor-only wiring bug ships undetected by the new tests. Mirror at least one observability scenario for --tool cursor or share test logic between tools.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/launch-review.sh:958; scripts/test-launch-review.sh:2140-2180
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] New failure-log wiring for cursor is not covered by the new observability tests (codex-only harness additions). Cursor-only bug in 7th-arg plumbing ships undetected. Add a small cursor IMPLEMENT_TMPDIR execution-issues assertion or shared helper.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: scripts/test-append-tool-failure.sh (no new cases in diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New dual-suffix and --transient-retry-count behavior not covered by the dedicated append-tool-failure harness. Regression in append-tool-failure.sh header composition slips until test-launch-review or production logs show wrong headers. Add assert_contains cases for combined auth/transient suffix and invalid transient-retry-count handling.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/test-launch-review.sh:954-1000
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SL-transient-obs-nontransient comment says no transient-retries field but tests require transient-retries=1. Maintainers or automation treating comments or the original plan as truth will ship the wrong contract or flip-flop behavior. Update the block comment and any spec to match the intended semantics (log M=1 vs omit field).
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/test-launch-review.sh:901-910,997-1001
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Substring greps for auth/transient retry counts can match unintended larger numbers. Counters such as 30 or 11 could satisfy patterns meant for 3 or 1, weakening regression detection if headers evolve. Use delimiter-aware regexes or structured asserts on the header line.
- **Suggested revision**: Address the concern above.


