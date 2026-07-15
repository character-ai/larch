# Review Round 1

- Mode: `diff`
- 9 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale `design-log-publish.sh` security references
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-tier1-doc-pointers
- **Severity**: major
- **Concern**: Live SECURITY.md prose at lines 317, 366, and 426 still points to deleted `design-log-publish.sh`, contradicting the documented Python publication and redaction paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-tier1-doc-pointers: Align both paragraphs with the breadcrumb rewrite: `python/cli.py run-log commit`, `python/cli.py design log-publish`, and `python/cli.py run-log publish-breadcrumbs` / `python/larch/report/run_log_commit.py`.


### FINDING_2: Valid in-repository symlinks rejected by pointer lint
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-tier1-doc-pointers
- **Severity**: minor
- **Concern**: The lint rejects every symlink before resolving it, so symlinks to existing regular files inside the repository are falsely reported as dead pointers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-tier1-doc-pointers: Match the enumeration contract: fail on missing paths and explicit root escape, but accept symlinks whose resolved path stays under `--root` and exists; add a fixture test for `python/live_via_symlink.py` → real file.


### FINDING_6: Whitespace filtering handles only ASCII spaces
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: minor
- **Concern**: Prefixed tokens followed by tabs or non-ASCII whitespace are treated as pointer candidates instead of being skipped, causing false lint failures.


### FINDING_7: Stale `read-session-env-key.sh` security reference
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: SECURITY.md describes plugin-root rehydration through the retired `read-session-env-key.sh` instead of the live `python/cli.py session read-key` path.


### FINDING_8: Directory paths accepted as document pointers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The lint uses existence alone, allowing a directory cited as a Tier-1 document pointer to pass validation.


### FINDING_11: Root canonicalization errors escape the tool contract
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: A symlink-loop or otherwise invalid `--root` can raise from `Path.resolve()` and produce a traceback instead of the required fixed diagnostic and exit code 2.


### FINDING_12: Stale `ship-pr-state.sh` security reference
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-tier1-doc-pointers
- **Severity**: major
- **Concern**: SECURITY.md attributes symlink rejection and atomic state writes to `ship-pr-state.sh`, obscuring the live implementation in `python/larch/implement/ship_state.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-tier1-doc-pointers: Rewrite the sentence to name `python/larch/implement/ship_state.py` (or `python/cli.py ship pr` state I/O) as the writer and keep `ship-pr-state.sh` only as the tmpdir filename if needed.


### FINDING_13: Stale `cleanup-tmpdir.sh` security reference
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-tier1-doc-pointers
- **Severity**: major
- **Concern**: SECURITY.md says cleanup is performed by deleted `cleanup-tmpdir.sh` rather than the live Python cleanup command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-tier1-doc-pointers: Replace the backtick token with `python/cli.py session cleanup-tmpdir` (or prose that the Python cleanup verb owns tmpdir reaping).


### FINDING_15: Missing edge-case test coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Tests do not cover the required non-regular-document, invalid-UTF-8, valid symlink-target, and related pointer-validation cases, leaving regressions in error handling and candidate validation undetected.
