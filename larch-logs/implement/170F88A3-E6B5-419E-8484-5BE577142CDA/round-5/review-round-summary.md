# Review Round 5

- Mode: `diff`
- 2 accepted, 8 rejected (4 neutral)

## Accepted Findings

### FINDING_1: correctness: `python/closeout.py` `_read_key` missing stdout capture breaks run-id rehydration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_read_key` invokes `subprocess.run` without capturing stdout, so `result.stdout` is `None` and `.strip()` raises `AttributeError` on success paths. Even when no crash occurs, CLI output is never returned, so Step 16 run-id and token-session rehydration from `session-env.sh`, `ship-pr-state.sh`, and `finalize-state.sh` fails silently. `write-rejected` and timing children receive empty `run_id` and token env; `/implement` Step 16-17 can log Tool Failures, omit summary markers when `summary-final.md` is empty, and write the rejected-findings run-log batch with `run_id=""`. The RUN_ID fallback chain has no pytest coverage, so regressions would not be caught in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add `capture_output=True` (or `stdout=subprocess.PIPE`) to `_run`/`_read_key` and guard stdout before `.strip()`.
  - From cursor-specialist-correctness-output.txt: Fix `_read_key` stdout capture; add a non-mocked integration test for `step_16_main` run_id fallback chain.
  - From cursor-specialist-testing-output.txt: Add tests seeding session-env, ship-pr-state, and finalize-state with distinct IDs and assert forwarded `--run-id`


### FINDING_14: architecture: missing `agent-lint.toml` excludes for new Makefile-only pytest modules
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The migration removed Makefile-only exclusions for `scripts/test-implement-finalize.sh`, `scripts/test-finalize-sanity-check.sh`, and `skills/implement/scripts/test-step-16-17.sh`, and added only a comment for `python/test_finalize.py` without an actual exclude entry. The replacement harnesses (`python/test_preflight.py`, `python/test_closeout.py`, `python/test_final_report.py`, `python/test_finalize.py`) are Makefile-only like `python/test_review_and_fix.py`, which is excluded. This branch likely reintroduces G004 dead-script false positives for the new pytest modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Add explicit `agent-lint.toml` exclude entries (with Makefile-only comments) for all four new test modules, mirroring the pattern used for `python/test_review_and_fix.py` and `python/test_implement_dispatch.py`.


