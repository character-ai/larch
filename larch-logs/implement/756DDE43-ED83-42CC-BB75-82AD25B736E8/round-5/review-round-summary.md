# Review Round 5

- Mode: `diff`
- 14 accepted, 18 rejected (11 neutral)

## Accepted Findings

### FINDING_10: helper CLI dispatch does not initialize quiet fd-3 routing
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: KV-emitting Python CLI verbs can write contract output to fd1 instead of inherited quiet fd3 when invoked from a Bash caller that already initialized quiet routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: ci failed-jobs missing legacy fixable jobs
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Python `ci failed-jobs` omits legacy fixable jobs such as `lint-local` and `bash32-check`, causing fixable failures to be emitted as unfixable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: create_pr_parity returns requested title for existing PRs
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Existing-PR race recovery can return `PR_STATUS=existing` with the requested title instead of the actual existing PR title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: baseline dirty probe mishandles failed subprocess output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Phantom baseline probing can parse stdout from a failed `check-mid-run-dirty-tree.sh` invocation as clean/dirty instead of treating the non-zero subprocess result as unknown, and tests mock away the subprocess contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: phantom_probe_main emits optional keys when empty
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: `phantom_probe_main` emits `PHANTOM_COUNT` and `PHANTOM_PATHS_FILE` even for clean probes with empty values, diverging from the optional-key Bash contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-contract-parity-output.txt: Address the concern above.


### FINDING_2: Migration cutover/deletion is incomplete
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python CLI verbs were added, but live runtime callers, docs, structure tests, manifest entries, and zero-live-caller script deletion are not fully cut over, leaving Bash and Python implementations to drift and acceptance criteria unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_21: ci status/wait validation is incomplete
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: `ci status` and `ci wait` skip Bash-parity validation for base labels and non-negative integer arguments, allowing invalid remotes/refs or negative counters to fall through into pending/timeout behavior or exceptions instead of the documented error surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt: Address the concern above.


### FINDING_22: gh run_logs CLI parity paths lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `gh run_logs_failed` / `gh_cli run_logs_main` lack tests for in-progress exit 3, failure exit 1, and raw tail behavior, so polling semantics can regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_23: pr_edit_body_file retry and optional-repo parity lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: PR body edit retry behavior and optional `--repo` handling are not covered, risking failed transient updates or fork/multi-remote regressions after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_26: snapshot_untracked failure/delete-output contract lacks tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Snapshot-untracked tests do not cover failure cleanup, sorted success output, or invalid argv avoiding output creation, so stale baseline files could cause false phantom positives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: rebase_push lacks transient retry parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `rebase_push` does not wrap fetch, `ls-remote`, and force-with-lease push operations with the transient retry behavior present in the Bash path, so network flakes can incorrectly fail or rerun rebases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_32: ci wait writes contract through raw stdout
- **Reviewer(s)**: dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: Non-`--output-file` `wait_main` writes contract lines via `sys.stdout.write` instead of `emit_kv` / contract stream, creating quiet-routing drift from other CI verbs and Bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-parity-output.txt: Address the concern above.


### FINDING_4: create_branch fetch lacks transient retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `create_branch` performs a single-shot fetch where the Bash helper retried transient failures, causing recoverable flakes to return `fetch_failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: ci failed-jobs usage errors return wrong exit code
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `ci failed-jobs` CLI usage errors return exit 1 instead of the Bash contract’s exit 2, which can make callers misclassify invalid argv as runtime failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


