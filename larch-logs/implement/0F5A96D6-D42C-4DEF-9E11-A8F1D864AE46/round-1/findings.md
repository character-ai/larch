### FINDING_1: **Important** `correctness` `scripts/ship-pr.sh:1497` — The new broad OID-mismatch match routes every `local HEAD ... does not match PR head OID` error into `run_rebase_rebump`, but `merge-pr.sh` uses that same error for non-recoverable divergence, including when local `HEAD` is behind the PR head OID (`scripts/merge-pr.md:58`). Concrete failing scenario: another process pushes commit `B` to the PR branch while this checkout is still at older commit `A`; `merge-pr.sh` emits the matching error, `run_rebase_rebump` rebases local `A`, and `git-force-push.sh` fetches the branch then force-pushes with a fresh lease, overwriting remote-only commit `B`. Narrow recovery to cases where the PR head OID is an ancestor of local `HEAD` before calling `run_rebase_rebump`, or have `merge-pr.sh` emit a distinct recoverable result/direction and only route that case; add a regression test for local-behind/non-ancestor mismatch staying stalled.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/ship-pr.sh:1497` — The new broad OID-mismatch match routes every `local HEAD ... does not match PR head OID` error into `run_rebase_rebump`, but `merge-pr.sh` uses that same error for non-recoverable divergence, including when local `HEAD` is behind the PR head OID (`scripts/merge-pr.md:58`). Concrete failing scenario: another process pushes commit `B` to the PR branch while this checkout is still at older commit `A`; `merge-pr.sh` emits the matching error, `run_rebase_rebump` rebases local `A`, and `git-force-push.sh` fetches the branch then force-pushes with a fresh lease, overwriting remote-only commit `B`. Narrow recovery to cases where the PR head OID is an ancestor of local `HEAD` before calling `run_rebase_rebump`, or have `merge-pr.sh` emit a distinct recoverable result/direction and only route that case; add a regression test for local-behind/non-ancestor mismatch staying stalled.
- **Suggested revision**: Address the concern above.

### FINDING_2: architecture: scripts/test-ship-pr.sh:1338-1380
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test setup diverges from plan text explicit ci-wait override and _make_rebase_stubs Plan listed dedicated ci-wait always-merge and _make_rebase_stubs; test uses default write_stubs ci-wait merge plus inline helper loop including refresh-run-logs.sh Document in test comment or align with _make_rebase_stubs pattern if maintainers want strict plan traceability
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/ship-pr.sh:1493-1499
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] record_failure for merge-pr envelope runs before the recoverable OID branch Operators may see a merge-pr envelope failure logged even when ship-pr exits 0 after run_rebase_rebump Reorder or conditionally skip record_failure when routing to is_head_divergence_recoverable run_rebase_rebump
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-ship-pr.sh:1361-1368
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New OID-mismatch test reimplements the stub loop from _make_rebase_stubs instead of composing that helper per implementation plan Helper list and chmod list can diverge from _make_rebase_stubs on future edits causing false test failures or missing coverage Call _make_rebase_stubs then overwrite ci-wait.sh and merge-pr.sh optionally extend _make_rebase_stubs to stub refresh-run-logs.sh for all rebump scenarios
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-ship-pr.sh:1361-1379
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Regression test uses ad hoc stubs instead of _make_rebase_stubs per plan Stub surface may drift from other rebase tests if helpers change Align test with _make_rebase_stubs or shared stub builder
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/ship-pr.sh:1173-1208
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Helper placed before run_rebase_rebump not after Plan first option was after run_rebase_rebump; behavior unchanged Accept as-is alternate placement or move after function if style guide prefers plan order
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/ship-pr.sh:1202-1206
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] is_head_divergence_recoverable name and glob may include merge-pr non-recoverable OID errors Merge-pr emits same substring for documented non-recoverable gate refusal; ship-pr will run_rebase_rebump instead of STALL_STEP=12d Confirm product intent; if stall must persist for those errors tighten matcher per merge-pr result codes or suffixes
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/ship-pr.sh:1202-1207
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] OID-mismatch substring also matches merge-pr 'after force-push recovery' errors, not only the same-version gate message. MERGE_RESULT=error with ERROR ending in 'after force-push recovery' routes to run_rebase_rebump and skips STALL_STEP=12d, changing operator-facing recovery semantics vs a narrow 'same-version gate' interpretation. Narrow the glob or document broader intent in scripts/ship-pr.md.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/ship-pr.sh:1202-1207 scripts/merge-pr.sh:205-208
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Glob matches merge-pr OID errors including after force-push recovery suffix merge-pr already attempted flush recovery; ship-pr may still invoke full rebase+rebump instead of 12d stall Narrow pattern or document that after-force-push OID mismatch is in scope for run_rebase_rebump
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/ship-pr.sh:1202-1207 scripts/ship-pr.sh:1497-1499
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] is_head_divergence_recoverable matches both merge-pr OID errors including the merge-pr-documented non-recoverable refusal suffix merge-pr.sh emits MERGE_RESULT=error with local HEAD vs PR head OID plus refusing to evaluate same-version gate when its own checks deem divergence unsafe; ship-pr no longer stalls at STALL_STEP=12d and instead runs run_rebase_rebump (rebase/sync/force-push path), changing outcomes versus a manual Step-16 stall Narrow the case pattern to the intended subset or document that ship-pr intentionally escalates past merge-pr refusal for all OID-mismatch gate errors
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/ship-pr.sh:1493-1499
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] record_failure for merge-pr envelope runs before OID recovery; recoverable path can exit 0 with a prior tool-failure append A run that self-heals via run_rebase_rebump still leaves a merge-pr tool failure in execution-issues while PHASE=done Skip envelope record_failure when is_head_divergence_recoverable applies or annotate superseded failure
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-ship-pr.sh:1338-1380
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] OID-mismatch test duplicates rebump stub wiring next to _make_rebase_stubs instead of extending the shared helper (plan named _make_rebase_stubs). Future run_rebase_rebump dependency changes may be wired in one helper but not the OID case (or vice versa), weakening regression signal until a failure surfaces in CI. Extend _make_rebase_stubs (or a shared _ensure_rebump_deps) and call it from oid_mismatch_recoverable; optionally assert STALL_TRACKING=false / STALL_STEP cleared.
- **Suggested revision**: Address the concern above.

