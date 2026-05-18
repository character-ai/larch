# Review Round 1

- Mode: `diff`
- Accepted findings: 2
- Rejected findings: 5
- Exonerated findings: 0
- Neutral findings: 5

## Accepted Findings

### FINDING_1: **Important** `correctness` `scripts/ship-pr.sh:1497` — The new broad OID-mismatch match routes every `local HEAD ... does not match PR head OID` error into `run_rebase_rebump`, but `merge-pr.sh` uses that same error for non-recoverable divergence, including when local `HEAD` is behind the PR head OID (`scripts/merge-pr.md:58`). Concrete failing scenario: another process pushes commit `B` to the PR branch while this checkout is still at older commit `A`; `merge-pr.sh` emits the matching error, `run_rebase_rebump` rebases local `A`, and `git-force-push.sh` fetches the branch then force-pushes with a fresh lease, overwriting remote-only commit `B`. Narrow recovery to cases where the PR head OID is an ancestor of local `HEAD` before calling `run_rebase_rebump`, or have `merge-pr.sh` emit a distinct recoverable result/direction and only route that case; add a regression test for local-behind/non-ancestor mismatch staying stalled.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/ship-pr.sh:1497` — The new broad OID-mismatch match routes every `local HEAD ... does not match PR head OID` error into `run_rebase_rebump`, but `merge-pr.sh` uses that same error for non-recoverable divergence, including when local `HEAD` is behind the PR head OID (`scripts/merge-pr.md:58`). Concrete failing scenario: another process pushes commit `B` to the PR branch while this checkout is still at older commit `A`; `merge-pr.sh` emits the matching error, `run_rebase_rebump` rebases local `A`, and `git-force-push.sh` fetches the branch then force-pushes with a fresh lease, overwriting remote-only commit `B`. Narrow recovery to cases where the PR head OID is an ancestor of local `HEAD` before calling `run_rebase_rebump`, or have `merge-pr.sh` emit a distinct recoverable result/direction and only route that case; add a regression test for local-behind/non-ancestor mismatch staying stalled.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/ship-pr.sh:1493-1499
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] record_failure for merge-pr envelope runs before the recoverable OID branch Operators may see a merge-pr envelope failure logged even when ship-pr exits 0 after run_rebase_rebump Reorder or conditionally skip record_failure when routing to is_head_divergence_recoverable run_rebase_rebump
- **Suggested revision**: Address the concern above.


