# Review Round 4

- Mode: `diff`
- 10 accepted, 10 rejected (6 neutral)

## Accepted Findings

### FINDING_10: `check-phantom-dirty` emits optional phantom keys on clean/tracked-only states
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: `git check-phantom-dirty` always emits `REASON`, `PHANTOM_COUNT`, and/or `PHANTOM_PATHS_FILE`, including clean or tracked-only cases where bash omits those optional keys. Consumers that key on presence can mis-detect phantom state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-parity-output.txt: Address the concern above.


### FINDING_11: `check-phantom-dirty` CLI lacks bash argv/parse-error parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: Invalid `check-phantom-dirty` argv can exit 1 without the expected `STATUS=unknown` contract stream, and the Python CLI drops `--phantom-paths-dir`, hard-wiring output to `IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-contract-parity-output.txt: Address the concern above.


### FINDING_12: Phantom baseline logic reimplements retained bash and misses failure classifications
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: `phantom.py` reimplements `check-mid-run-dirty-tree.sh --mode baseline` instead of delegating as planned, skipping or drifting from bash behavior around path validation, NUL sorting/merge behavior, non-UTF-8 baseline handling, and `STATUS=unknown` failure tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt: Address the concern above.


### FINDING_16: `rebase_push` retry/equality behavior does not match `rebase-push.sh`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python `rebase_push()` uses a force-push recovery path with fewer retries and less exact re-fetch/equality recovery than bash. Transient failures that bash would recover on later attempts can become Python exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_17: `pr create` passes `--repo ""` when repo resolution fails
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When repo resolution fails, Python can pass an empty repo string to gh helpers, producing `--repo ""` instead of either omitting `--repo` or failing early with a clear setup error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_18: `poll_ci` downgrades passing checks with failed PR view instead of triggering bash-equivalent rebase
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When checks pass but `pr_view_ok` is false, Python can downgrade to pending/wait, whereas bash would feed the conflicted state into `ci-decide` and trigger rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: `ci wait --output-file` lacks trap/finally publishing parity
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Signal or exception exits during `ci wait --output-file` can skip writing the output file or `.done` sentinel, leaving consumers blocked or missing default bail KVs compared with bash trap behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_20: `rebase_push` lacks direct contract/parity tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The complex live Python `rebase_push` exit/flag surface is not directly tested, so conflict or validation regressions could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: `create_pr_parity` lacks coverage for existing-PR and exit-code cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `create_pr_parity()` is untested for existing PR title handling and exit 1/2 surfaces, risking wrong `PR_TITLE` or cutover exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_28: `poll_ci` retry synthesis drops conflicted and PR-view state
- **Reviewer(s)**: dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: On consecutive empty/error status reads, `poll_ci` rebuilds a pending `CiStatus` while dropping `conflicted` and `pr_view_ok`, unlike bash retry behavior that preserves the parsed conflict state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-parity-output.txt: Address the concern above.


