# Review Round 3

- Mode: `diff`
- 6 accepted, 6 rejected (5 neutral)

## Accepted Findings

### FINDING_1: correctness: missing model-args preflight exit-matrix tests (Codex and Cursor)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required model-args preflight exit-matrix tests are missing for Codex and Cursor although `agents.py` implements both paths. If `resolve_model_args` regresses, the launcher could write wrong exit codes or dirty-tree `STATUS` without CI catching it. Collector retry and dirty-tree contracts for model-args failures can drift without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest cases stubbing `resolve_model_args` to raise; assert exit 1, preflight bundle, and unknown dirty-tree for each tool.
  - From cursor-specialist-testing-output.txt: Monkeypatch `resolve_model_args` to raise and assert exit code, dirty-tree `STATUS=unknown`, and preflight bundle.


### FINDING_13: risk-integration: Cursor empty-result retry and Codex quota-gated retry untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: Cursor empty-result retry and Codex quota-skip-before-transient-retry are untested. Transient retry alone is covered; empty-result and quota-gated retry regressions would surface only in production review runs. The plan requires pytest proof that Cursor exit-0 empty `.result` retries when `LARCH_CURSOR_RETRY_EMPTY_RESULT` is enabled, does not retry when it is `0`, and reacquires the external serial lock on each attempt; `test_launch_review.py` only exercises empty output via `_review_cursor_postprocess` and has no stub-launcher test asserting attempt counts or lock acquisition for the retry loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `_review_run_with_retries` unit tests for empty Cursor result and quota sidecar cases.
  - From dyn-launcher-parity-output.txt: Add integration tests with a fake `cursor` binary that returns `{"result":""}` on the first N invocations, monkeypatch/spy `external_serial_lock_acquire`, and assert retry count and lock calls with `LARCH_CURSOR_RETRY_EMPTY_RESULT` set to `1` vs `0`.


### FINDING_16: security: Codex preamble temp file read before flush/close
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The Codex review preamble is written to a `NamedTemporaryFile`, then `_prepare_codex_home()` reads that path before the handle is flushed or closed. The read can see an empty file, so `CODEX_HOME/config.toml` may omit the strict read-only `instructions` block while still launching Codex.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Flush and close the temp file before calling `_prepare_codex_home()`, or write the instructions with a closed `Path.write_text()` temp path.


### FINDING_17: correctness: unguarded `_num()` on Cursor `usage.outputTokens`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Cursor post-processing calls `_num()` on `usage.outputTokens` outside a `try`. If Cursor returns a valid result with a non-numeric usage field, the launcher raises after the vendor succeeded, before dirty-tree writing and `.done` promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Catch `ValueError` here and treat invalid usage as `0`, matching the tolerant path in `_record_cursor_usage_from_output()`.


### FINDING_2: correctness: pre-existing worktree dirt must not become reviewer dirt (untested)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: Plan edge case "pre-existing worktree dirt must not become reviewer dirt" has no integration test exercising real baseline capture. A baseline-diff bug could mark clean Cursor reviews `DIRTY_DETECTED` and discard valid reviewer output during collection. Existing tests stub out `_review_write_cursor_dirty_tree_from_baseline`, so regressions in `dirty_tree.baseline` git delta and sidecar emission through `agent launch-review` would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add test with pre-launch untracked baseline file and assert post-run dirty-tree sidecar stays clean.
  - From cursor-specialist-testing-output.txt: Add stub-cursor integration test with pre-existing untracked files asserting baseline sidecar fields and no false reviewer dirt.
  - From dyn-launcher-parity-output.txt: Add a test that writes a real NUL untracked baseline via `git snapshot-untracked`, leaves pre-existing untracked files unchanged across a stub Cursor launch, and asserts the emitted `.dirty-tree` sidecar is `STATUS=clean` while new reviewer-created untracked files yield `STATUS=dirty` with populated `NEW_UNTRACKED_PATHS_FILE`.


### FINDING_3: correctness: invalid `LARCH_TOKEN_BUDGET_CAP_REVIEW` values untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Invalid `LARCH_TOKEN_BUDGET_CAP_REVIEW` values are not tested though `_review_effective_token_cap` ignores non-positive env. Misconfigured env like `0` or `abc` might accidentally cap launches if `_is_positive_int` regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add tests with invalid env values asserting vendor stub still runs.


