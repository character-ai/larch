### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `scripts/git-push.sh:36-49` — Failed `git push` attempts are reported as success. After `if git push; then ... fi` runs with a failing push, `$?` at line 39 is the status of the `if` compound, which is `0`, so three failed pushes end with `exit 0`; `ship-pr.sh` can then treat an unpushed CI-fix commit as pushed. Store the push status in an `else` branch or run `git push; rc=$?` with `set +e`, then exit with that captured non-zero status. Add a stubbed failing-push regression test.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/git-push.sh:36-49` — Failed `git push` attempts are reported as success. After `if git push; then ... fi` runs with a failing push, `$?` at line 39 is the status of the `if` compound, which is `0`, so three failed pushes end with `exit 0`; `ship-pr.sh` can then treat an unpushed CI-fix commit as pushed. Store the push status in an `else` branch or run `git push; rc=$?` with `set +e`, then exit with that captured non-zero status. Add a stubbed failing-push regression test.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## correctness: scripts/git-push.sh:41-44

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] First retry jitter collapses to fixed 1s. Minor mismatch vs documented ±25% on first backoff. Adjust jitter divisor or document fixed first delay.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/rebase-push.sh:253-265` — The new force-push retry loop does not recover the lease race it documents. If `git push --force-with-lease` fails because the remote branch advanced after fetch, attempts 2 and 3 repeat the same stale lease without fetching/rebasing, so the retry only delays the same failure. Refresh and re-evaluate state between attempts, or route this push path through the existing lease recovery primitive and document the actual semantics.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/rebase-push.sh:253-265` — The new force-push retry loop does not recover the lease race it documents. If `git push --force-with-lease` fails because the remote branch advanced after fetch, attempts 2 and 3 repeat the same stale lease without fetching/rebasing, so the retry only delays the same failure. Refresh and re-evaluate state between attempts, or route this push path through the existing lease recovery primitive and document the actual semantics.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## code-quality: scripts/ship-pr.sh:1131-1159

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Comment claims a phase-wide FIX_ATTEMPTS cap but the while loop only limits attempts per run_evaluate_failure call; each re-entry resets _fix_attempt. A long CI loop that repeatedly calls run_evaluate_failure can still exceed five vendor fix pushes overall while operators believe a global cap exists. Reword the comment to per-invocation semantics or enforce a true budget via read_state FIX_ATTEMPTS and document it.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## code-quality: scripts/test-apply-bump.sh:2730-2745 scripts/test-apply-bump.md:2684

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Docs promise a WARN line on stderr for tolerated internal artifacts; sub-test I never asserts stderr. WARN output could regress without CI noticing, undermining the phantom-file observability goal. Assert stderr contains WARN and the tolerated basenames using the harness stderr log.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `scripts/rebase-push.sh:258-275` — The new force-push retry refreshes the branch ref after a `--force-with-lease` failure, then retries with the default lease. Concrete failing scenario: remote `origin/feature` advances from `A` to another runner’s `B`; this script’s first push fails the lease, line 263 refreshes the tracking ref to `B`, and the retry can now lease against `B` and overwrite it with this local `HEAD`. Preserve the original expected remote OID for all retries, e.g. use `--force-with-lease=refs/heads/$CURRENT_BRANCH:$expected_oid`, and only treat refreshed remote equality with local `HEAD` as success; otherwise fail or rebase rather than retrying against the refreshed lease.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/rebase-push.sh:258-275` — The new force-push retry refreshes the branch ref after a `--force-with-lease` failure, then retries with the default lease. Concrete failing scenario: remote `origin/feature` advances from `A` to another runner’s `B`; this script’s first push fails the lease, line 263 refreshes the tracking ref to `B`, and the retry can now lease against `B` and overwrite it with this local `HEAD`. Preserve the original expected remote OID for all retries, e.g. use `--force-with-lease=refs/heads/$CURRENT_BRANCH:$expected_oid`, and only treat refreshed remote equality with local `HEAD` as success; otherwise fail or rebase rather than retrying against the refreshed lease.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:1110-1160

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] run_evaluate_failure mixes legacy exit_stall token 12c with new 12-max-retries and 12-detached-head strings. Automation or runbooks that parse STALL_STEP now need special cases for the same ci-merge evaluate_failure phase depending on which branch was taken. Unify naming (e.g. rename the empty FAILED_RUN_ID stall to 12-missing-run-id) or document 12c as the sole legacy exception in ship-pr.md and any consumer docs.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:1142-1187

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] New STALL_STEP strings (10-max-retries, 12-max-retries, 10-detached-head, 12-detached-head) replace coarser tokens on some exhaustion paths. External automation that matched old STALL_STEP values may mis-handle stalls after upgrade. Document token churn in ship-pr contract / release notes for operators.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:1143-1187,scripts/ship-pr.sh:1155-1161

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] STALL_STEP values for vendor/rebase exhaustion and detached HEAD changed from numeric-style 10 / 12c to hyphenated strings (10-max-retries, 12-max-retries, 10-detached-head, 12-detached-head). Downstream automation or docs that key off exact STALL_STEP=10 or STALL_STEP=12c for evaluate-failure exhaustion will no longer match; stalls may be mis-routed or ignored in custom tooling. Update every consumer of STALL_STEP to accept the new tokens, or add a parallel machine-readable reason field while keeping legacy stall codes stable.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Nit** `risk-integration` `scripts/ship-pr.md:66-77` — The new docs say `REBASE_COUNT >= 5`, but line 72 still says an existing `REBASE_COUNT >= 20` guard bounds the retry budget, and line 77 still says `run_evaluate_failure` runs one vendor fix attempt. Update these stale statements to match the new 5-attempt behavior.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `risk-integration` `scripts/ship-pr.md:66-77` — The new docs say `REBASE_COUNT >= 5`, but line 72 still says an existing `REBASE_COUNT >= 20` guard bounds the retry budget, and line 77 still says `run_evaluate_failure` runs one vendor fix attempt. Update these stale statements to match the new 5-attempt behavior.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## code-quality: .claude/skills/bump-version/scripts/apply-bump.md:54-55

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] First invariant still says worktree must be clean before the next bullet tolerates internal untracked files. Quick read suggests a contradiction with the new tolerance rule. Reword the first invariant to forbid only non-internal dirty states (single coherent bullet).
- **Suggested revision**: Address the concern above.

