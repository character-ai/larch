# Review Round 2

- Mode: `diff`
- 10 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: step5c_core ambient env overrides rehydrated session identity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-env-ctx-output.txt, dyn-dyn-quiet-routing-output.txt
- **Severity**: important
- **Concern**: `step5c_core` builds `ctx` with `{**env, **os.environ, **normalized_overrides}`, so ambient shell/process env can override rehydrated `ISSUE_NUMBER`, `SESSION_ID`, `REPO`, and related session keys. Publish, pause, and render argv driven from `ctx` can therefore target the wrong issue/repo/session while the session-env file still describes the active design run. Separately, `cleanup_eligible` and `_step5c_write_status` still read `SESSION_ID` and `STANDALONE_HEAVY_FAILED` from the raw rehydrate `env` dict, so publish metadata and Step 5c status/cleanup gates can diverge when ambient and rehydrate values differ.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use rehydrate-wins merge {**os.environ, **env, **normalized_overrides} or take session identity only from rehydrate env
  - From cursor-specialist-correctness-output.txt: Thread ctx.session_id and related fields through cleanup_eligible and status sidecar writes
  - From dyn-dyn-env-ctx-output.txt: Route all Step 5c session metadata through one source: either pass `ctx` into `_step5c_write_status` and use `ctx.session_id` / `ctx.str_value(...)` for `cleanup_eligible`, or build `ctx` with rehydrate-winning merge (`{**os.environ, **env, **normalized_overrides}`) and use `ctx` everywhere, including status sidecar writes.
  - From dyn-dyn-env-ctx-output.txt: Match the validator recipe and use `{**os.environ, **env, **normalized_overrides}` so rehydrated session keys win except where `normalized_overrides` explicitly replaces them; update the ambient-override test to expect session-file authority, or restrict ambient precedence to non-session keys only.
  - From dyn-dyn-quiet-routing-output.txt: Keep the normalized-wins `ctx` for tmpdir/pid, but assemble publish argv from rehydrate `env` (or a session-only slice), or flip merge precedence for session-authoritative keys so rehydrate beats ambient for `--issue` / `--session-id` / `--repo`.


### FINDING_3: Incomplete fd-3 contract-test migration for design lifecycle cores
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-quiet-routing-output.txt
- **Severity**: important
- **Concern**: Plan-required fd-3 contract capture migration is incomplete after `quiet_init` moved into cores. Many direct `step5c_core` and `step_final_summary_core` tests still assert contract KVs (`PUBLISH_RC`, `STEP5C_STATUS`, `LARCH_FINAL_SUMMARY_*`) via `capsys` after `quiet_init` in cores. With `conftest.py` forcing `LARCH_QUIET_DISABLE=1`, those tests may pass via fd dup luck and miss real quiet-enabled core routing or nested `_capture_contract_stream_to_paths` regressions; production emits contract output on fd 3 only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Migrate remaining step5c_core and step_final_summary_core contract tests to _capture_core_contract
  - From cursor-specialist-testing-output.txt: Migrate all direct step5c_core and step_final_summary_core contract tests to _capture_core_contract or inherited-quiet fd-3 capture.
  - From dyn-dyn-quiet-routing-output.txt: Migrate the remaining direct-core contract assertions to `_capture_core_contract` (or the inherited-quiet pipe pattern), and keep at most a small CLI-path `capsys` smoke layer.


### FINDING_7: stale_paths omits computed done sentinel suffix
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `stale_paths` cleanup hardcodes `.done` and `.inner.done` but not the computed done suffix. A prior run's custom or alternate sentinel file can survive cleanup and make the next poll treat a stale completion as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Include the computed done path (and supported legacy suffixes) in stale_paths before Popen.


### FINDING_8: Missing env IPC leak regression tests after core return
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-dyn-quiet-routing-output.txt
- **Severity**: important
- **Concern**: Missing post-return env leak regression for removed IPC keys. `FINAL_SUMMARY_PATH` or `SUMMARY_OUTCOME` could leak past `*_core` restore and poison a later in-process step. Plan-called regressions for `step5c_core` / `step_final_summary_core` env restoration are still absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert pre/post os.environ snapshots around step5c_core for those keys.
  - From dyn-dyn-quiet-routing-output.txt: Add the three regressions from the plan so env IPC removal and core-only `quiet_init` ownership stay guarded.


### FINDING_9: Missing symlink parity test for ctx.design_tmpdir vs publish argv
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-dyn-quiet-routing-output.txt
- **Severity**: important
- **Concern**: Missing symlink parity test for `ctx.design_tmpdir` vs publish `--design-tmpdir`. Stale rehydrate symlink path could diverge from resolved publish argv on symlinked `DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add step5c_core test with symlinked session env asserting resolved paths match.
  - From dyn-dyn-quiet-routing-output.txt: Add the three regressions from the plan so env IPC removal and core-only `quiet_init` ownership stay guarded.


### FINDING_10: Missing step_final_summary_main quiet_init absence regression
- **Reviewer(s)**: dyn-dyn-quiet-routing-output.txt
- **Severity**: important
- **Concern**: Plan called for a regression that `step_final_summary_main` does not call `quiet_init`; this guard is still absent, weakening confidence in core-only `quiet_init` ownership on the quiet-routing refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-quiet-routing-output.txt: Add the three regressions from the plan so env IPC removal and core-only `quiet_init` ownership stay guarded.


### FINDING_11: Missing validator_autofix_main post-resolve ctx.design_tmpdir assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing `validator_autofix_main` post-resolve `ctx.design_tmpdir` assertion. `_validator_pause_save` could see pre-resolve tmpdir on symlink validation fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Record ctx.design_tmpdir in pause stub and assert resolved path after validator_autofix_main.


### FINDING_13: Staged architectural guideline fingerprint can pin stale diff
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Staged guideline notes can be pinned against a newer code diff because `_staged_fingerprint_valid()` only checks that the saved snapshot hashes to the saved fingerprint. `note_fingerprint_stale()` repeats the same shortcut at `python/architectural_guidelines.py:400-407`, so a code-changing retry can leave the old `architectural-guideline-materialized-diff.txt` in place and still surface a stale assessment on the PR or final report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Compare the stored fingerprint to a freshly materialized live diff when `repo_root` and `base_ref` are available, with any intended log-only exemption applied explicitly.


### FINDING_14: Shell wrapper sources writable materialize.env artifact
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The wrapper sources `$IMPLEMENT_TMPDIR/architectural-guideline-materialize.env`, which is a writable run artifact. If a prior step or tool writes `BASE_REF=$(...)` or similar shell syntax into that file, this line executes it under the orchestrator user before calling Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Do not source this file. Parse only `BASE_REF=` and `DIFF_FINGERPRINT=` as inert text, then validate the base ref and 64-char hex fingerprint before passing them as argv.


### FINDING_15: render_final_summary_main treats explicit empty argv as omitted
- **Reviewer(s)**: dyn-dyn-env-ctx-output.txt
- **Severity**: important
- **Concern**: `render_final_summary_main` resolves IPC-threaded metadata with `session_id_arg or os.environ.get("SESSION_ID", "")` and `issue_number_arg or os.environ.get("ISSUE_NUMBER", "")`. An explicit empty `--issue-number` or `--session-id` is falsy, so the function falls back to ambient env even when the caller passed the flag deliberately (converted cores always pass these flags from `ctx`). That breaks the plan's argv-first rule and can resurrect stale `ISSUE_NUMBER` / `SESSION_ID` into summaries when `ctx` intentionally carries empty strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-env-ctx-output.txt: Track flag presence separately (for example `issue_number_set: bool` plus value, or `None` vs `""`), and use env fallback only when the flag was omitted, not when it was passed as an empty string.


