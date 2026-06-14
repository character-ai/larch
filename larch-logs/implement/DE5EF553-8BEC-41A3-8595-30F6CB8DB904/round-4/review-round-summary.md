# Review Round 4

- Mode: `diff`
- 8 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale `.diag` / Codex `.events.jsonl` on retryable retries
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On transient (and auth) retries, only `.sidecar` is rotated into `.sidecar.history`; `.diag` and Codex `.events.jsonl` from the failed attempt are left in place. A later successful retry can leave stale quota/network diagnostics that `classify_launch_failure` or operators may attribute to the successful run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On every retryable retry (transient and auth), reset `.diag` and Codex `.events.jsonl` the same way `.sidecar` is reset, or delete stale sidecars before re-invoking `run_external_agent`.


### FINDING_10: Codex prompt replay false-positive on embedded sentinel token
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Codex prompt replay treats any `LARCH_PROMPT_SENTINEL=1` line anywhere in a prompt file as a compact sentinel. A normal full prompt that quotes this token in feature text or plan can fail retry with `malformed prompt sentinel` or hash mismatch instead of replaying prompt bytes verbatim.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Only parse the compact sentinel when it appears at the start of the file or after the exact collector retry header. Otherwise, fall back to reading the prompt file verbatim.


### FINDING_11: `CODEX_HOME` can land inside output tree via `TMPDIR`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `CODEX_HOME` is created with `tempfile.TemporaryDirectory()` using the process default temp root. If `TMPDIR` points inside the reviewer output directory, Codex home lands inside the same tree passed via `--add-dir`, violating planned isolation that keeps `CODEX_HOME` outside the output tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Create the Codex home under a fixed external temp root, or resolve it and fail closed if it is under `output.parent`.


### FINDING_2: Cursor post-processing runs on non-zero exit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_review_cursor_postprocess` runs after both success and non-zero exits. Cursor can exit 1 with partial JSON containing a non-empty `.result`; post-processing then overwrites the output file with review prose while `.done` still records failure, producing contradictory artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Gate `_review_cursor_postprocess` on `result.exit_code == 0`, matching the branch that appends `cursor-status: ok`.


### FINDING_3: Gitleaks allowlist omits `python/test_launch_review.py`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.gitleaks.toml` allowlist description names `python/test_launch_review.py`, but `paths` never adds `^python/test_launch_review\.py$` after removing `scripts/test-launch-review.sh`. Pytest fixtures with realistic `sk-ant-…` or PEM-shaped strings (planned for secret-leak argv tests) can fail pre-commit/CI while the description implies exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add `^python/test_launch_review\.py$` to the `paths` array (same pattern as `python/test_review_and_fix.py`).
  - From cursor-specialist-edge-cases-output.txt: Add ^python/test_launch_review\.py$ to the paths allowlist (or remove it from the description until the regex exists)
  - From cursor-specialist-testing-output.txt: Add ^python/test_launch_review\.py$ to the gitleaks paths allowlist.


### FINDING_4: Collector review retries omit `--timing-task-kind`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Outer review retries in `scripts/collect-agent-results.sh` invoke `agent launch-review` without `--timing-task-kind`; `launch_review_main` then defaults to generic `codex-review` / `cursor-review`. A slot launched as e.g. `codex-review-round-2-correctness` that retries on empty output records timing under the generic key, splitting one logical reviewer task across two ledger keys and breaking per-slot cost/timing reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Persist `OUTER_LAUNCHER_TIMING_KIND` in `.meta` during launch (or derive from existing `LARCH_TIMING_TASK_KIND` env) and forward it on collector replay.


### FINDING_6: Missing launch-failure / design-only pytest coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required pytest for launch-failure logging is absent after deleting `scripts/test-launch-review.sh`. Cases not covered include design-only failure logging to `DESIGN_TMPDIR/execution-issues.md` when `IMPLEMENT_TMPDIR` is unset, implement-path logging, run-log append-failure site review Step 2, and vendor-diagnostics staging. Regressions could pass CI unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the missing tests from the plan’s security and launch-failure sections before relying on deleted shell harness coverage.
  - From cursor-specialist-edge-cases-output.txt: Add stubbed tests for _review_append_launch_failure covering design-only and implement paths
  - From cursor-specialist-testing-output.txt: Add pytest cases that force final vendor failure with only DESIGN_TMPDIR set, only IMPLEMENT_TMPDIR set, and assert run-log append-failure site review Step 2 plus vendor diagnostics helper invocation.


### FINDING_7: Missing security/isolation pytest parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted shell harness security/isolation tests are not fully replaced in `python/test_launch_review.py`. Missing coverage includes `CODEX_HOME` outside output tree, distinct `CURSOR_CONFIG_DIR` per parallel launch, argv/artifact secret non-leakage, symlink/control-char add-dir rejection, and in-output add-dir acceptance. Regressions in `_review_validate_codex_add_dir` or per-launch temp homes could widen Codex sandbox or leak config across parallel Cursor reviewers without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the missing tests from the plan’s security and launch-failure sections before relying on deleted shell harness coverage.
  - From cursor-specialist-edge-cases-output.txt: Port the plan's four security/isolation pytest cases from the deleted shell harness
  - From cursor-specialist-testing-output.txt: Add stub-binary tests for symlink rejection, in-output acceptance, CODEX_HOME placement, and secret absence from CMD_JSON/meta.


