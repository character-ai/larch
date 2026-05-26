### FINDING_10: risk-integration: scripts/test-breadcrumb-monitor.sh:1940-1967
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing boundary malformed-PID cases (0, 33-byte cap, non-ASCII). Regressions in positive-integer or byte-sanitization logic could slip through while existing malformed loop cases still pass. Extend the malformed_case table with 0, max-length, and non-ASCII payloads.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: scripts/breadcrumb-monitor.sh:107-114
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] LARCH_BM_TEST_TIMEOUT_SECONDS is honored in production without a test-only guard. Stray exported LARCH_BM_TEST_TIMEOUT_SECONDS=60 causes monitors to SIGTERM/KILL Family B jobs after 60s instead of 1800s. Gate override behind LARCH_BM_TEST_MODE=1 or restrict to test harness invocation only.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: scripts/breadcrumb-monitor.sh:198-205
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Length check runs before newline strip while writer always appends newline. Hypothetical 32-digit PID plus newline rejected as malformed; timeout does not signal target process. Strip one trailing newline before len>32 check; add max-width PID harness case.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/breadcrumb-monitor.sh:198-205
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] PID length check runs before stripping one trailing newline, not after as the plan specifies. A 32-digit PID with a single trailing newline (33 raw bytes) would emit WARN paired-pid-file-missing and skip signaling despite matching the plan’s post-strip limit. Move the >32-byte rejection to after the optional final-newline strip, or compute length on the stripped payload only.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/test-lib-quiet.sh:209-209
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Atomic-write test does not verify the trailing newline the plan requires. A regression that wrote only digits without `\n` would still pass because command substitution strips trailing newlines from `cat` output. Assert exact bytes (e.g., `cmp` against `printf '%s\n' "$written_pid"` or `wc -c` equals `${#written_pid}+1`).
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/breadcrumb-monitor.sh:571
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] larch_bm_validate_path LARCH_LOG_ROOT override applies to all monitor paths but is undocumented. Operators reading breadcrumb-monitor.md may not understand why paths under repo larch-logs no longer validate when session tmpdir env vars are unset. Document the disabled larch-logs fallback in breadcrumb-monitor.md path validation section.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/test-lib-quiet.sh:2096
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Paired PID atomic-write test does not assert trailing newline in the written file. A regression to writing PID without newline could pass tests while changing monitor read semantics. Assert exact file contents with cmp against printf '%s\n' "$written_pid".
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: scripts/breadcrumb-monitor.sh:198-205
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] PID length check runs before stripping one trailing newline, contradicting plan/doc overlong rule after strip. A 32-digit PID plus newline (33 bytes from dd) is rejected as malformed and never receives SIGTERM/SIGKILL on monitor timeout. Apply the >32-byte check after stripping one optional final newline; add a harness case if desired.
- **Suggested revision**: Address the concern above.


### FINDING_7: risk-integration: scripts/test-lint-foreground-markers.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Missing harness fixture for run-step2-dispatch.sh paired-PID linter rules. A regression in family_b_pid_writer_required or fence_has_paired_pid_* for that basename could ship while test-lint-foreground-markers still passes; only full-tree lint on skills/implement/SKILL.md would catch it. Add assert_case_clean (and optional negative) fence for skills/implement/scripts/run-step2-dispatch.sh with mktemp/export and --paired-pid-file on the monitor line.
- **Suggested revision**: Address the concern above.


