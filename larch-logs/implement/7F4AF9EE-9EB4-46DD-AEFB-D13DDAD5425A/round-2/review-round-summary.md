# Review Round 2

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Quiet-load failure replays WARN/ERROR from both primary and stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-step3-contracts-output.txt, dyn-warn-replay-output.txt
- **Severity**: important
- **Concern**: On `read_result_env_main` / quiet-load failure (`rc != 0`), `_step3_normalize_load_env` Stage 1 replays `WARN=`/`ERROR=` from the regular primary `.step3-review-result.env` and again from the stdout fallback (`selected_source`), violating the single-source contract. Duplicate machine lines can appear before the canonical KV envelope and break orchestrator fence expectations (`test-step3-orchestrator-fence.sh` “replayed exactly once”). Legacy Bash recovery replayed only from captured loop stdout on failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step3-contracts-output.txt: Gate the `if primary_regular: _step3_replay_warn_error_safe(result_env)` block on `rc == 0` from `_step3_read_result_env_quiet`, or branch explicitly on failure so Stage 1 replays only `selected_source` (the stdout fallback) and Stage 2 overlay semantics stay unchanged.
  - From dyn-warn-replay-output.txt: Gate Stage 1 on successful quiet load: when `rc == 0` and `primary_regular`, replay `result_env`; when `rc != 0`, replay only `selected_source` (stdout fallback). Drop the unconditional `if primary_regular: replay(result_env)` on the failure branch.


### FINDING_2: Empty-primary fallback not reflected in `selected_source`; `ERROR=` can be dropped
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt, dyn-step3-contracts-output.txt, dyn-warn-replay-output.txt
- **Severity**: important
- **Concern**: `_step3_read_result_env_quiet` binds `selected_source` to the regular primary path even when `read_result_env_main` internally falls back to `--fallback-input` because the primary is empty or has no allowlisted KVs. Stage 1 then replays the empty/wrong file; Stage 2 overlay replays `WARN=` only (not `ERROR=`). Values may load from stdout while `ERROR=` lines present only on captured loop stdout are dropped before the canonical envelope, diverging from documented `selected_source` semantics and legacy Bash behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Mirror the empty-primary fallback selection. Return `selected_source=fallback` when `read_result_env_main` used the fallback, then replay selected-source `WARN=` / `ERROR=` exactly once before overlay.
  - From dyn-step3-contracts-output.txt: After the quiet `read_result_env_main` call, if `rc == 0` and the primary is regular but zero-length (or `phase_driver_read_result_env(primary, allow)` is empty), set `selected` to the fallback path when it is a readable regular file; add a pytest case with a 0-byte `.step3-review-result.env` and `WARN=` only on captured stdout.
  - From dyn-warn-replay-output.txt: Mirror `read_result_env_main` source selection in the quiet helper (including the empty-primary retry) and return that path as `selected_source`. Stage 1 should call `_replay_warn_error` exactly once on that path; keep Stage 2 overlay `WARN=` gated on `primary_regular` as today.


### FINDING_5: Missing subprocess test for missing-result stdout/stderr routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required missing-result KV-only stdout/stderr subprocess test was not added when wrapper grep pins were removed. Post-loop markdown warnings moved to Python; the wrapper no longer greps for `**⚠ Step 3` on stdout. A regression printing missing-result warnings to stdout would pass `make test-design-step3-state` and orchestrator-fence tests that only check exit codes and KV keys.
- **Suggested revisions (informational for voters; coder decides)**:


