# Review Round 1

- Mode: `diff`
- 4 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: consumer-repo fallback bypasses sessions-cache scratch
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `_path_is_repo_related` keys repo-related detection off the plugin `_REPO_ROOT` instead of the active checkout, so consumer-repo `log_root` values can miss the sessions-cache fallback and leave run-log payload temps under the working tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_2: step 7a passes an unsupported `--tmpdir` to run-log commit
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: The Step 7a flush path invokes run-log commit with `--tmpdir`, but the commit CLI does not accept that flag, so the commit subprocess exits on argument parsing and log publication is degraded or skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: OOS parse failures can raise instead of returning a controlled failure
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: In the code-review OOS path, `_parse_artifact` does not catch `ScratchDirError`, so a missing scratch directory can crash parsing instead of returning the controlled `_fail(...)` envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_12: tempfile baseline occurrence is off by one for `lint_mermaid_fences.py`
- **Reviewer(s)**: dyn-dyn-tempfile-ratchet
- **Severity**: major
- **Concern**: The baseline row for `larch/lint/lint_mermaid_fences.py:main` uses `occurrence: 2`, but the scanner counts the outer unqualified `TemporaryDirectory` as occurrence 1 and ignores the inner `mkdtemp(..., dir=tmpdir)`, so the live identity is unbaselined and `python/cli.py lint tempfile-dir` exits 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-tempfile-ratchet: Address the concern above.


