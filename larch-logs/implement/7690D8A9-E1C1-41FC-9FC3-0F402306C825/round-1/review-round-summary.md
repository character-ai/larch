# Review Round 1

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 4
- Exonerated findings: 4
- Neutral findings: 3

## Accepted Findings

### FINDING_1: **Important** `correctness` `scripts/git-push.sh:36-49` — Failed `git push` attempts are reported as success. After `if git push; then ... fi` runs with a failing push, `$?` at line 39 is the status of the `if` compound, which is `0`, so three failed pushes end with `exit 0`; `ship-pr.sh` can then treat an unpushed CI-fix commit as pushed. Store the push status in an `else` branch or run `git push; rc=$?` with `set +e`, then exit with that captured non-zero status. Add a stubbed failing-push regression test.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/git-push.sh:36-49` — Failed `git push` attempts are reported as success. After `if git push; then ... fi` runs with a failing push, `$?` at line 39 is the status of the `if` compound, which is `0`, so three failed pushes end with `exit 0`; `ship-pr.sh` can then treat an unpushed CI-fix commit as pushed. Store the push status in an `else` branch or run `git push; rc=$?` with `set +e`, then exit with that captured non-zero status. Add a stubbed failing-push regression test.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/git-push.sh:41-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] First retry jitter collapses to fixed 1s. Minor mismatch vs documented ±25% on first backoff. Adjust jitter divisor or document fixed first delay.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `risk-integration` `scripts/rebase-push.sh:253-265` — The new force-push retry loop does not recover the lease race it documents. If `git push --force-with-lease` fails because the remote branch advanced after fetch, attempts 2 and 3 repeat the same stale lease without fetching/rebasing, so the retry only delays the same failure. Refresh and re-evaluate state between attempts, or route this push path through the existing lease recovery primitive and document the actual semantics.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/rebase-push.sh:253-265` — The new force-push retry loop does not recover the lease race it documents. If `git push --force-with-lease` fails because the remote branch advanced after fetch, attempts 2 and 3 repeat the same stale lease without fetching/rebasing, so the retry only delays the same failure. Refresh and re-evaluate state between attempts, or route this push path through the existing lease recovery primitive and document the actual semantics.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/ship-pr.sh:1131-1159
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Comment claims a phase-wide FIX_ATTEMPTS cap but the while loop only limits attempts per run_evaluate_failure call; each re-entry resets _fix_attempt. A long CI loop that repeatedly calls run_evaluate_failure can still exceed five vendor fix pushes overall while operators believe a global cap exists. Reword the comment to per-invocation semantics or enforce a true budget via read_state FIX_ATTEMPTS and document it.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/test-apply-bump.sh:2730-2745 scripts/test-apply-bump.md:2684
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Docs promise a WARN line on stderr for tolerated internal artifacts; sub-test I never asserts stderr. WARN output could regress without CI noticing, undermining the phantom-file observability goal. Assert stderr contains WARN and the tolerated basenames using the harness stderr log.
- **Suggested revision**: Address the concern above.


