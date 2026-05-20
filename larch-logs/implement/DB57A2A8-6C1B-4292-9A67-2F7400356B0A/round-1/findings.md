### FINDING_1: [OUT_OF_SCOPE] security: scripts/append-tool-failure.sh:139-150
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Pre-existing: markdown header fields (site tool status verdict) are not fully sanitized for markdown/control characters beyond partial newline checks on some fields. Malicious or accidental values could alter markdown structure of execution-issues; unchanged by this branch. Hardening would be a separate hardening change outside this PR scope.
- **Suggested revision**: Address the concern above.

### FINDING_2: architecture: scripts/append-tool-failure.sh:143-147
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Only the dual-flag and retry-only branches emit retry metadata; transient-only is silently ignored. A future caller passes only --transient-retry-count expecting observability and gets no retry suffix. Add transient-only branch or document and reject unsupported combinations.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/append-tool-failure.sh:143-147
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Transient-only --transient-retry-count (no --retry-count) emits no retry suffix. Hypothetical future caller passes only transient count and silently loses observability. Add transient-only elif or reject the flag combination in fail_usage.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-launch-review.sh:954-1000
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SL-transient-obs-nontransient comment says no transient-retries field but tests require transient-retries=1. Maintainers or automation treating comments or the original plan as truth will ship the wrong contract or flip-flop behavior. Update the block comment and any spec to match the intended semantics (log M=1 vs omit field).
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-launch-review.sh:954-1000
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Test comment says failure entry WITHOUT transient-retries field but assertion requires grep match on transient-retries=1. Readers and future edits assume wrong contract; risk of “fixing” tests to match the wrong comment and breaking observability intent. Align comment (and any spec) with the asserted contract or change assertions to match the documented contract.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-launch-review.sh:954-957
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Block comment says failure entry lacks transient-retries but assertions require transient-retries=1. Maintainers or reviewers trust the comment and mis-diagnose a failing test or “wrong” product behavior. Rewrite the comment to document transient-retries=1 means evaluated with no transient retry; align with append-tool-failure.md.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/append-tool-failure.sh:143-147
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Header logic only adds transient metadata when BOTH RETRY_COUNT and TRANSIENT_RETRY_COUNT are non-empty. A caller passes only --transient-retry-count expecting it in the log line; suffix omits transient entirely. Add elif for transient-only or document unsupported combination explicitly in append-tool-failure.md.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/test-launch-review.sh:899-900,950-951,995-996
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New execution-issues counts use grep -c with || echo 0 and a bare codex-review substring. Zero-match exit-status quirks or capture-body mentions of codex-review can skew counts. Use robust counting or anchor patterns to the markdown header line.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/test-launch-review.sh:901-910,997-1001
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Substring greps for auth/transient retry counts can match unintended larger numbers. Counters such as 30 or 11 could satisfy patterns meant for 3 or 1, weakening regression detection if headers evolve. Use delimiter-aware regexes or structured asserts on the header line.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/test-launch-review.sh:954-1000
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Case comment says failure log WITHOUT transient-retries but assertions require transient-retries=1. A maintainer removes the grep check to match the comment and drops coverage of the non-retry observability path. Update the SL-transient-obs-nontransient comment to describe transient-retries=1 as the expected no-retry signal.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/test-launch-review.sh:954-1001
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] SL-transient-obs-nontransient contradicts implementation plan assertion (c) and the case comment: plan and comment require no transient-retries substring; test requires grep match on transient-retries=1. Operators or reviewers following the plan or the adjacent test comment conclude the log must omit transient-retries=, but CI enforces the opposite; the branch is self-inconsistent as written. Align plan bullet (c), the case comment, and assertions with one contract (either omit transient-retries= on this path or document and assert transient-retries=1 everywhere).
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/test-launch-review.sh:997-1000; implementation plan SL-transient-obs-nontransient (c)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Shipped tests require transient-retries=1 on non-transient failure; plan bullet (c) said the line must not contain transient-retries=. Review gate or implementer follows (c) and strips the 7th arg or changes tests, conflicting with Edge cases and docs. Reconcile the implementation plan checklist with the chosen log semantics (and with append-tool-failure.md).
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-launch-review.sh:997-1000; implementation plan checklist (c)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Shipped tests require transient-retries=1 on non-transient failure; plan bullet (c) said the line must not contain transient-retries=. Review gate or implementer follows (c) and strips the 7th arg or changes tests, conflicting with Edge cases and docs. Reconcile the implementation plan checklist with the chosen log semantics (and with append-tool-failure.md).
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/launch-review.sh:958 and scripts/test-launch-review.sh cursor subshell
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cursor path receives TRANSIENT_ATTEMPT in append_launch_failure but new observability tests run only under the codex suite. Cursor-only wiring bug ships undetected by the new tests. Mirror at least one observability scenario for --tool cursor or share test logic between tools.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/launch-review.sh:958; scripts/test-launch-review.sh:2140-2180
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] New failure-log wiring for cursor is not covered by the new observability tests (codex-only harness additions). Cursor-only bug in 7th-arg plumbing ships undetected. Add a small cursor IMPLEMENT_TMPDIR execution-issues assertion or shared helper.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/launch-review.sh:958; scripts/test-llaunch-review.sh (cursor suite)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] New failure-log wiring for cursor is not covered by the new observability tests (codex-only). Cursor-only bug in 7th-arg plumbing ships undetected. Add a small cursor IMPLEMENT_TMPDIR execution-issues assertion or shared helper.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-append-tool-failure.sh (no new cases in diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New dual-suffix and --transient-retry-count behavior not covered by the dedicated append-tool-failure harness. Regression in append-tool-failure.sh header composition slips until test-launch-review or production logs show wrong headers. Add assert_contains cases for combined auth/transient suffix and invalid transient-retry-count handling.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-launch-review.sh:899-900,950-951,995-996
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] grep -c ... || echo 0 can yield wrong counts when the file exists and match count is zero. Future launcher behavior that touches execution-issues.md before failure could make SL-transient-obs-fired count assertion fail or flake. Replace with a counting idiom that treats grep exit status 1 with output 0 as success without appending a second zero.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-launch-review.sh:899-900,995-996
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] grep -c 'codex-review' can overcount if the substring appears outside the header line. Future stub or log body includes codex-review in captured text; assertion reports multiple entries or misleading count. Anchor grep to the header pattern or count structured bullets.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-launch-review.sh:997-1000 vs implementation plan
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Implemented non-transient test expects transient-retries=1 while the written plan bullet expected absence of transient-retries=. Plan-driven review rejects green CI as not meeting written acceptance. Reconcile issue/plan acceptance with implemented semantics (or change code if absence was truly required).
- **Suggested revision**: Address the concern above.

