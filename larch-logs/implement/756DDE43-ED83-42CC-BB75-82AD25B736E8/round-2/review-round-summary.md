# Review Round 2

- Mode: `diff`
- 19 accepted, 10 rejected (7 neutral)

## Accepted Findings

### FINDING_1: remote_branch_state emits unredacted ls-remote failures
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `remote_branch_state` can expose raw git/auth/network failure text through `ERROR=` output, unlike the bash path that redacts `git ls-remote` failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: retired-script lint misses live ship-pr reference forms
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `migration_lint` does not reliably detect all live `ship-pr` references to retired helpers, including bare basename/source forms and some `$SCRIPT_DIR`-derived paths, so live helpers could be deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: push_cli force_main disables retry sleep
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `force_main` injects a no-op sleeper into `force_push_recovery`, eliminating the legacy 5-second wait and making transient lease races fail more often.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: existing-PR push recovery disables retry sleep
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_push_open_pr_branch` also disables `force_push_recovery` sleep, so open-PR force-push recovery loses the bash retry delay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: rebase --continue guard checks only git-dir
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Python `--continue` guard does not check for `rebase-merge` or `rebase-apply`, so no-active-rebase cases can fall through to `git rebase --continue` and emit non-canonical failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: conflict discovery helpers can raise instead of returning controlled conflict output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `conflict_files` and `unmerged_paths` use raising git helpers on parity-sensitive paths, so bad repo/transient failures can crash CLIs instead of returning conflict KVs or controlled exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: remote_branch_state lacks legacy transient retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `remote_branch_state` does not preserve the bash transient retry envelope around `ls-remote`, causing flakes to return error/stall where the legacy helper would retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: pr create is not argv-compatible with create-pr.sh
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `pr create` newly requires `--repo` and `--branch`, so legacy-compatible invocations with only title/body fail before deriving repo/current branch and emitting expected PR KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_19: ci failed-jobs contract diverges from retired script
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `ci failed-jobs` lacks the legacy `--output-tsv`, `FAILED_JOBS_*` keys, reason tokens, stdout shape, and in-progress/error exit-code mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: pr CLI skips repo slug validation before gh mutation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `pr create` and `pr body-update` accept malformed or attacker-influenced `--repo` values without the validation enforced by the legacy shell wrappers, risking unintended cross-repo mutation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_20: empty sanitized CI job names are counted
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Failed job rows whose sanitized names become empty are still counted, producing inflated failed-job counts versus legacy behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_21: rebase_push uses origin instead of resolved push remote and legacy push loop
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `rebase_push` force-pushes `origin` rather than resolving branch `pushRemote`/tracking remote and preserving the legacy retry/noop/PUSH_ERROR contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: poll_ci budget exhaustion discards last CI snapshot
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-behavioral-parity-output.txt
- **Severity**: important
- **Concern**: On poll-budget exhaustion, `poll_ci` returns a synthetic pending/zero snapshot instead of preserving the last polled CI status, losing diagnostics such as `FAILED_RUN_ID`, `CONFLICTED`, and counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-behavioral-parity-output.txt: Address the concern above.


### FINDING_26: _squash_merge_race can abort status on git log failure
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_squash_merge_race` throws on best-effort `git log` probe failure, so CI status can abort without required KV output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_37: ci rerun-failed contract diverges from retired script
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `ci rerun-failed` emits `RERUN_ALREADY_RUNNING`, causing callers that parse `ALREADY_RUNNING` to count already-running workflows against retry budget differently from the legacy script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_38: ci wait publish/done-write failure returns wrong exit code
- **Reviewer(s)**: dyn-robustness-output.txt
- **Severity**: important
- **Concern**: After a successful poll, `wait_main` returns exit `1` on output publish or `.done` write failure, whereas legacy behavior reserves exit `1` for usage errors and relies on absent `.done` for fail-closed consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-robustness-output.txt: Address the concern above.


### FINDING_7: create_pr_parity trusts mismatched --branch
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: `create_pr_parity` can be invoked with a `--branch` that differs from the checked-out branch, causing PR discovery or creation for stale/different code than what was pushed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.


### FINDING_8: new PR creation uses plain git push instead of upstream HEAD push
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The new-PR path uses bare `git push`, which can fail on fresh local branches without upstreams and may not match the legacy `git push -u origin HEAD` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: ci wait --output-file lacks trap/finally sentinel publication
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-robustness-output.txt
- **Severity**: important
- **Concern**: `ci wait --output-file` only publishes output and `.done` after normal `poll_ci` return; exceptions or trap-deliverable termination after stale cleanup can leave consumers waiting forever.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-robustness-output.txt: Address the concern above.


