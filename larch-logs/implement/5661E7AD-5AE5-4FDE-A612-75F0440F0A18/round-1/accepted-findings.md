### FINDING_1: **Important** `correctness` `scripts/launch-review.sh:521-524`, `scripts/launch-review.sh:925-928`, affected: `scripts/run-external-agent.sh:122-127`, `scripts/run-external-agent.sh:204-225`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/launch-review.sh:521-524`, `scripts/launch-review.sh:925-928`, affected: `scripts/run-external-agent.sh:122-127`, `scripts/run-external-agent.sh:204-225`      The transient retry gate uses the outer launcher wall-clock elapsed time with a `<= 5s` cutoff, but `run-external-agent.sh` defaults to a 10s poll interval. Concrete failing scenario: with `RUN_EXTERNAL_AGENT_POLL_INTERVAL` unset, a Codex child that exits 7 immediately with no output can still be observed by the wrapper’s first `kill -0`, then the wrapper sleeps 10s before returning; `_ELAPSED` is about 10, so `external_is_transient_infra_failure` returns 1 and the requested retry never happens. The new tests set `RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05`, so they do not exercise production timing. Fix by removing the elapsed cutoff, making it exceed the wrapper’s default poll interval, or making the wrapper detect child exit without waiting a full poll cycle before the retry classifier measures elapsed. Verification note: I attempted `bash scripts/test-lib-external-launcher-common.sh` and `bash scripts/test-launch-review.sh`, but this environment is read-only and both failed at `mktemp` with `Operation not permitted`. `git diff --check $(git merge-base HEAD main)..HEAD` completed successfully.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: scripts/test-launch-review.sh:866
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Self-referential ln -sf leaves a bogus codex stub path after transient tests instead of restoring the default stub. Future tests appended after this line could invoke the wrong binary or a broken symlink; comment promises behavior the command does not implement. Restore the default stub explicitly (rewrite real file or ln -sf to a dedicated backup path), not "$STUB_BIN/codex" -> "$STUB_BIN/codex".
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/test-lib-external-launcher-common.md:6
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract lists sidecar-based branches (/dev/null sidecar missing sidecar) that the function and tests do not implement. Readers expect tests that do not exist; conflicts with lib-external-launcher-common.md output-file semantics. Update the md to describe output-file absent/empty/nonempty and elapsed checks only.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: scripts/test-launch-review.sh:844-863
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] SL-transient-not-applied omits RC assertion. A regression that exits 0 incorrectly could slip by if stub invocation count stays at one. Assert the launcher exit code for exit-1 stub behavior.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/test-lib-external-launcher-common.md:7
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Contract doc describes sidecar-based guards and branches that do not exist in code or tests. Readers may add wrong tests or mis-diagnose production behavior (transient signal is output file size, not sidecar). Rewrite the bullet list to describe output-file absent/empty/non-empty and elapsed/exit allowlist only; drop /dev/null sidecar wording.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: scripts/test-lib-external-launcher-common.md:7;scripts/test-lib-external-launcher-common.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Part E promised /dev/null and unreadable sidecar tests; the harness does not include them while the sibling md claims sidecar-oriented coverage. Stale contract: documented branches are not exercised; Part E completeness against the plan fails. Update test-lib-external-launcher-common.md to the actual API; add the missing test cases or change the function to match the plan’s sidecar tests.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/test-launch-review.sh:865-866
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Post-suite ln -sf restores codex by linking codex to itself; it does not restore the default stub after transient-specific symlinks. Future tests appended after this block could run against codex-transient-noapply while believing the default stub is restored. Restore the original stub from a preserved path or re-emit the default heredoc stub.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: scripts/test-launch-review.sh:865-866
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Codex stub restore uses self-referential ln -sf and does not restore the default hermetic stub. Future tests inserted after this block could invoke the wrong stub; comment promises restore that does not happen. Mirror cursor pattern: ln -sf to the real default stub script path (or recreate the here-doc stub file).
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: scripts/test-lib-external-launcher-common.md:1-9
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Contract claims /dev/null sidecar and missing sidecar coverage that the library and tests do not implement. Operators or later edits may assume sidecar semantics that do not exist, leading to incorrect “fixes” or tests. Update the markdown to match output-file-based checks and actual test cases.
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: scripts/test-lib-external-launcher-common.md:7-8
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Sibling contract describes sidecar-based branches that the implementation and tests do not use. Maintainer adds wrong tests or “fixes” the helper based on stale sidecar semantics; doc contradicts scripts/lib-external-launcher-common.md. Rewrite the paragraph to document output-file checks (absent/empty/nonempty, elapsed) and align with lib-external-launcher-common.md.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/test-launch-review.sh:731-764
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comments describe empty sidecar though classification uses empty output file. Misleading guidance when debugging exit 7/8 retries vs auth. Reword comments to reference OUTPUT and run-external-agent cleanup behavior.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: scripts/test-launch-review.sh:857-866
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Restore line links codex to itself after prior ln -sf replaced the real stub. Future tests after this line would execute a broken self-symlink; current suite passes only because nothing runs after. Recreate the original stub file or ln -sf to a stable golden stub path.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: scripts/test-launch-review.sh:865-866
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Post-transient-tests codex restore uses ln -sf from codex to itself after codex was replaced by symlinks to transient stubs; default heredoc stub is not restored. No further codex assertions run today so CI can pass; adding tests after this line would still invoke the wrong codex stub or hit a circular symlink. Restore like cursor suite: keep default stub at a stable path (e.g. codex-sl) and ln -sf to it, or remove the dead restore if the subshell truly ends here.
- **Suggested revision**: Address the concern above.


