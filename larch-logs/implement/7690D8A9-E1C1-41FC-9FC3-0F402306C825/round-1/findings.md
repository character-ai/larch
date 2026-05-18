### FINDING_1: **Important** `correctness` `scripts/git-push.sh:36-49` — Failed `git push` attempts are reported as success. After `if git push; then ... fi` runs with a failing push, `$?` at line 39 is the status of the `if` compound, which is `0`, so three failed pushes end with `exit 0`; `ship-pr.sh` can then treat an unpushed CI-fix commit as pushed. Store the push status in an `else` branch or run `git push; rc=$?` with `set +e`, then exit with that captured non-zero status. Add a stubbed failing-push regression test.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/git-push.sh:36-49` — Failed `git push` attempts are reported as success. After `if git push; then ... fi` runs with a failing push, `$?` at line 39 is the status of the `if` compound, which is `0`, so three failed pushes end with `exit 0`; `ship-pr.sh` can then treat an unpushed CI-fix commit as pushed. Store the push status in an `else` branch or run `git push; rc=$?` with `set +e`, then exit with that captured non-zero status. Add a stubbed failing-push regression test.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` `scripts/rebase-push.sh:253-265` — The new force-push retry loop does not recover the lease race it documents. If `git push --force-with-lease` fails because the remote branch advanced after fetch, attempts 2 and 3 repeat the same stale lease without fetching/rebasing, so the retry only delays the same failure. Refresh and re-evaluate state between attempts, or route this push path through the existing lease recovery primitive and document the actual semantics.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/rebase-push.sh:253-265` — The new force-push retry loop does not recover the lease race it documents. If `git push --force-with-lease` fails because the remote branch advanced after fetch, attempts 2 and 3 repeat the same stale lease without fetching/rebasing, so the retry only delays the same failure. Refresh and re-evaluate state between attempts, or route this push path through the existing lease recovery primitive and document the actual semantics.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: skills/implement/references/rebase-rebump-subprocedure.md
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Reference text still emphasizes falling through to 12c while ship-pr now emits richer stall tokens. Operators reading only the subprocedure may misunderstand new stall outcomes; file was not updated in this diff. Optionally refresh the subprocedure doc to mention 12-max-retries / 12-detached-head tokens.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/rebase-push.sh:38-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Top exit-code banner omits detached HEAD under exit 2 Readers rely on header not .md; incomplete contract Update header exit 2 bullet for detached HEAD push guard
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/ship-pr.sh:1131-1159
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Comment claims a phase-wide FIX_ATTEMPTS cap but the while loop only limits attempts per run_evaluate_failure call; each re-entry resets _fix_attempt. A long CI loop that repeatedly calls run_evaluate_failure can still exceed five vendor fix pushes overall while operators believe a global cap exists. Reword the comment to per-invocation semantics or enforce a true budget via read_state FIX_ATTEMPTS and document it.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-apply-bump.sh:2730-2745 scripts/test-apply-bump.md:2684
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Docs promise a WARN line on stderr for tolerated internal artifacts; sub-test I never asserts stderr. WARN output could regress without CI noticing, undermining the phantom-file observability goal. Assert stderr contains WARN and the tolerated basenames using the harness stderr log.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:96-107
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Filter only ?? lines; ignored untracked !! not tolerated If internal artifacts are gitignored bump still fails Also filter !! lines or forbid ignoring those patterns
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/compose-review-findings.sh:57-71
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] escape_finding_body double-encodes existing HTML entities Reviewer text with &lt; becomes &amp;lt; in output Avoid double-encoding or document input contract
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/git-push.sh:36-48
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Retries all push failures not only transient NFF races Permanent push errors delayed by unnecessary sleeps Classify errors before retry or document broader retry
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/git-push.sh:41-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] First retry jitter collapses to fixed 1s. Minor mismatch vs documented ±25% on first backoff. Adjust jitter divisor or document fixed first delay.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/ship-pr.sh:1155-1178
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Same STALL_STEP values for rebump REBASE_COUNT cap and evaluate_failure exhaustion Telemetry cannot distinguish rebase-storm cap from vendor-repair cap without parsing fail_file Use distinct STALL_STEP strings or add STALL_REASON to state
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/ship-pr.sh:2581-2583
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment claims 5 total FIX_ATTEMPTS across calls; loop is per run_evaluate_failure Maintainer misconfigures related limits believing a global cap Reword comment to per-invocation vendor attempts
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-apply-bump.sh:2730-2745
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Sub-test I omits stderr WARN assertion required by plan WARN logging can regress unnoticed Add assert_stderr_contains for WARN prefix
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: branch diff vs implementation_plan
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Extra changes (compose-review, plugin bump, larch-logs) outside listed plan files Review scope creep vs stated plan Split PRs or amend plan doc for bundled work
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/git-push.sh:26-49
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Retry loop fires for any git push failure, not only non-FF / concurrent-tip races. Permanent failures (hooks, auth, branch rules) still sleep and retry up to three times, delaying accurate failure reporting. Restrict retries to classified transient signatures (e.g. non-fast-forward text) or exit immediately on other failures.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/ship-pr.sh:1155-1160
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] STALL_STEP for vendor exhaustion changed from 12c (ci-merge) to 12-max-retries Automation or docs keyed on STALL_STEP=12c no longer fires after five failed vendor fixes; stall handling misroutes Update SKILL/operator tables; add backward-compatible alias; or document migration
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/ship-pr.sh:1159 scripts/ship-pr.md:2532-2533
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Evaluate-failure exhaustion now uses STALL_STEP 10-max-retries / 12-max-retries instead of prior 10 / 12c-style tokens for that path. Runbooks or scripts matching only STALL_STEP=12c miss the new terminal stall and skip recovery actions. Document the migration and update external matchers or central stall constants.
- **Suggested revision**: Address the concern above.

