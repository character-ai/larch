# Review Round 5

- Mode: `diff`
- 3 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Missing transient retries in fork setup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Python fork setup no longer retries transient failures for `git ls-remote`, mirror push, and submodule update. A single network flake can abort setup or sync where the prior bash helper retried.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Issue creation can leave orphaned issues on non-numeric JSON id
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `issue create-one` treats successful `gh issue create` JSON with `number` and `url` but a non-numeric `id` as failure. It does not resolve the numeric REST id or roll back the created issue, leaving an open orphan and allowing duplicate reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Sparse allowlist regression guard is tautological
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The sparse allowlist regression guard compares the library against itself. Incorrect `LARCH_SPARSE_DIRS` edits can pass CI while upgrade and release flows reconcile the wrong marketplace cone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

