# Review Round 4

- Mode: `diff`
- 11 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_1: head-changed/forbidden-path terminate delegate on first occurrence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `head-changed` and `forbidden-path` terminate the delegate on first occurrence instead of consuming a cycle and continuing to `CI_AGENTIC_FIX_MAX_CYCLES`. Claude triggers forbidden-path or HEAD drift on cycle 1; cycles 2–20 never run despite plan calling for cycle-local rollback and continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat head-changed forbidden-path verify-failed and no-progress as non-terminal cycle outcomes; only emit ci-fix-exhausted after max_cycles.


### FINDING_14: mixed fixable/unfixable CI failures allow partial push
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The agentic fixer only bails when there are zero fixable jobs, so a mixed CI failure like `python-tests` plus `gitleaks` still launches Claude, verifies only the fixable job, and can push a partial fix while a known no-local-equivalent job is still failing. That regresses the prior `run_ci_fix` behavior, which carried `classified.unfixable` forward and rolled back instead of pushing when any unfixable job was present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Treat `classified.unfixable` as terminal before launching Claude, or at least block push and emit `STATUS=local-unfixable` with the unfixable job list.


### FINDING_15: passive ci wait ignores rebase ACTION and BEHIND_COUNT
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The passive `ci wait` result ignores `ACTION=rebase` and `ACTION=rebase_then_evaluate`. If main advances while the delegate is waiting, `ci wait` can report a failed run with `BEHIND_COUNT>0` and `ACTION=rebase_then_evaluate`, but the delegate treats it as another failed CI cycle and launches Claude again on a stale branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: After `ci wait`, route `ACTION in {"rebase", "rebase_then_evaluate"}` or positive `BEHIND_COUNT` to `STATUS=rebase-required` / `CI_FIX_REBASE_PENDING=true` instead of continuing the agentic fix loop.


### FINDING_16: _wait_for_ci ignores subprocess return code and malformed output
- **Reviewer(s)**: dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: `_wait_for_ci()` ignores the `ci wait` subprocess return code and parses only the output file (or stdout fallback). On wait crash, timeout, or empty/malformed output, the cycle is treated as `pushed` with detail `ci-failed-after-push` and the loop continues. That assumes a successful push and a failed CI run without a reliable `ACTION`/`CI_STATUS`/`FAILED_RUN_ID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-delegate-output.txt: Fail the cycle (rollback or explicit terminal status) when `ci wait` exits non-zero, the output file is missing/empty, or required KV keys are absent. Only continue when `FAILED_RUN_ID` or a definitive fail/pass status is parsed.


### FINDING_17: _agentic_fix_result parses contract KV from stderr
- **Reviewer(s)**: dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: `_agentic_fix_result()` parses KV from `result.stdout + "\n" + result.stderr`. Any stderr line matching `KEY=value` can override delegate contract keys (`STATUS`, `FIX_ATTEMPTED`, `CI_FIX_REBASE_PENDING`, etc.). A polluted stderr stream could mis-map to `pushed`/`fix-exhausted` and drive `monitor()`/`ship.py` down the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-delegate-output.txt: Parse stdout only, or parse only recognized keys from the tail of stdout after a sentinel, and treat stderr as diagnostic-only.


### FINDING_20: bare ======= lines falsely treated as unresolved conflict markers
- **Reviewer(s)**: dyn-conflict-loop-output.txt
- **Severity**: important
- **Concern**: `_path_has_conflict_markers` treats any line starting with `=======` as an unresolved conflict (`_CONFLICT_MARKER_RE` has no `<<<<<<<` / `>>>>>>>` context). Correctly merged files that legitimately contain a `=======` line (markdown rules, banners, test fixtures) can never be accepted, forcing unnecessary tier churn and eventual `PrePushConflictHandoff` / `Stalled`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-conflict-loop-output.txt: Require a full conflict-marker triplet (or at minimum a `<<<<<<<` / `>>>>>>>` pair) before treating a file as conflicted; treat bare `=======` lines as data unless they sit between recognized conflict headers.


### FINDING_25: launch_claude_lint_fix_main promotes raw stdout to primary output file
- **Reviewer(s)**: dyn-lint-claude-output.txt
- **Severity**: important
- **Concern**: On several non-success paths, `launch_claude_lint_fix_main` writes raw `result.stdout` to the primary `--output` file (`claude.log`) before any redaction. Only `.diag` is passed through `redact_tmpdir_paths` / `redact_secrets_only`. If Claude echoes prompt material in JSON or error text, that can land unredacted in session artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-lint-claude-output.txt: Never promote raw stdout to the primary output file; write a fixed sentinel (`CLAUDE_LINT_FIX_MALFORMED_JSON`, etc.) and keep the raw stream redacted in `.diag` only, matching the fail-closed promotion rules used for `launch-claude-subprocess`.


### FINDING_4: cycle-1 health failures route to first-fixer-non-health instead of in-delegate retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: Cycle-1 Claude health failures (auth, quota, `health-probe`, transient infra, binary-missing) return `STATUS=first-fixer-non-health`, routing to autonomous main-agent CI-fix and terminating the delegate. Cycles 2+ treat health as `waterfall-failed` and continue. Transient infra on the first launcher attempt therefore skips the 20-cycle delegate and routes through `monitor()` → `Outcome.NEEDS_USER_INPUT` / Exit 3 `first-fixer-non-health` instead of internal retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return waterfall-failed or a dedicated health status for health-class launcher failures; reserve first-fixer-non-health for non-health failures.
  - From cursor-specialist-edge-cases-output.txt: Emit distinct health status or retry in-delegate; do not map health to first-fixer-non-health.
  - From dyn-ci-delegate-output.txt: Reserve the cycle-1 `first-fixer-non-health` exit for non-recoverable cases (e.g. `binary-missing`, `auth`). Continue the loop for `health-probe`/quota/transient health, or retry health failures for at least N cycles before surfacing `first-fixer-non-health`.


### FINDING_5: plan-mandated agentic loop behavioral tests largely missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-specified agentic loop tests are largely missing; many `test_ci_monitor.py` cases are skipped. Regressions in 20-cycle behavior, push guards, passive CI wait, or KV mapping may ship undetected. Only KV/parser edge cases exist today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add plan-listed test_ci_agentic_fix cases and rewrite skipped monitor tests for the delegate path.
  - From cursor-specialist-testing-output.txt: Add stub-runner integration tests for _run_cycle/main covering each plan-listed path.


### FINDING_6: first-tier short-circuit uses parse_launcher_failure_class instead of effective_failure_class
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-conflict-loop-output.txt
- **Severity**: latent
- **Concern**: Conflict short-circuit uses `parse_launcher_failure_class` instead of `effective_failure_class` per plan. `make_conflict_launch_fn` always sets `failure_log`, and `parse_launcher_failure_class` maps a capture file with no `LAUNCHER_FAILURE_CLASS` KV to `health`, not `attempt.failure.failure_class`. A first-tier semantic non-health failure therefore falls through to Codex/Cursor unless the launcher envelope carries `LAUNCHER_FAILURE_CLASS=other`, even when `classify_launch_failure` already classified the attempt as `other`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use agents.effective_failure_class(attempt) for index==0 short-circuit logic.
  - From dyn-conflict-loop-output.txt: Use `agents.effective_failure_class(attempt)` for short-circuit decisions (or write `LAUNCHER_FAILURE_CLASS` into every capture before classification).


### FINDING_8: classify_launch_failure missing auth_verdict and LAUNCHER_FAILURE_CLASS inputs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: `_run_cycle` calls `agents.classify_launch_failure()` without `auth_verdict` or `binary_present`, unlike `agents._append_ci_failure()`. Agentic cycle re-classifies Claude launcher failures without `auth_verdict` or `LAUNCHER_FAILURE_CLASS` from launcher stdout. Auth/quota failures can be classified as `other` instead of `health`. On cycle 2+, `other` exits immediately as `first-fixer-non-health` instead of continuing the agentic loop like a health failure would, breaking parity with the launcher and conflict waterfall health-continuation semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Parse LAUNCHER_FAILURE_CLASS from launch_tier capture or pass external_auth_verdict and binary_present into classify_launch_failure.
  - From dyn-ci-delegate-output.txt: Mirror the launcher call: pass `auth_verdict=agents.external_auth_verdict("claude", diag, output)`, set `binary_present` from the launcher preflight/`shutil.which("claude")`, and/or read `LAUNCHER_FAILURE_CLASS` from the capture file before applying the cycle-1 short-circuit.


