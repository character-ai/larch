# Review Round 1

- Mode: `diff`
- 10 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: step1e re-entry omits step-3-terminal and persist sidecar cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-sentinel-contract-output.txt, dyn-embedded-assets-output.txt
- **Severity**: important
- **Concern**: Gate B/C `step1e_reentry_main` clears `step-3` and `step-3.5` but not `.completed/step-3-terminal` or `.step3-terminal-persisted-this-run`. After a mid-loop bail-out with a persisted envelope, stale terminal markers can survive re-entry. Foreground probes or `marker_step_completed` may report DONE and authorize parsing stale `.step3-review-result.env` before the next Step 3 wrapper relaunch clears sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Unlink .completed/step-3-terminal and .step3-terminal-persisted-this-run in step1e_reentry_main and extend test_step1e_reentry_removes_expected_sentinels
  - From codex-specialist-correctness-output.txt: Unlink `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` in the Step 1e re-entry cleanup.
  - From cursor-specialist-edge-cases-output.txt: Add step-3-terminal and .step3-terminal-persisted-this-run to the step1e unlink list and extend test_step1e_reentry_removes_expected_sentinels
  - From cursor-specialist-testing-output.txt: Unlink .completed/step-3-terminal and .step3-terminal-persisted-this-run in step1e_reentry_main; extend test_step1e_reentry_removes_expected_sentinels to assert removal.
  - From dyn-sentinel-contract-output.txt: Extend `step1e_reentry_main` to unlink `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run`, mirror the cleanup in `python/test_design_lifecycle.py::test_step1e_reentry_removes_expected_sentinels`, and document the path in `scripts/hook-bg-poll-guard.md` next to the other re-entry cleaners.
  - From dyn-embedded-assets-output.txt: Extend `step1e_reentry_main` to unlink `$design_tmpdir/.completed/step-3-terminal` and `$design_tmpdir/.step3-terminal-persisted-this-run`, update `test_step1e_reentry_removes_expected_sentinels` in `python/test_design_lifecycle.py` to seed and assert removal of both paths, and update the Step 1e re-entry row in `skills/design/SKILL.md` (~99) so the sentinel table matches the Python implementation.


### FINDING_10: missing runtime test for persist-success step-3-terminal contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required runtime test is missing for loop persist success writing `step-3-terminal` and persist failure not writing it. Only static grep covers `step3_loop_write_terminal_step3`; breaking the persist-success guard in `step3_loop_persist_envelope` would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness that stubs phase_driver_write_result_env success/failure and asserts step-3-terminal and sidecar presence/absence accordingly.


### FINDING_11: wrapper trap unconditionally mints step-3 on non-terminal bail-outs
- **Reviewer(s)**: dyn-sentinel-contract-output.txt
- **Severity**: important
- **Concern**: The plan documents mid-loop bail-outs as possibly having `step-3-terminal` without `step-3`, and routes Step 3b only on `step-3`. `_step3_review_guarantee_completed_sentinels` still unconditionally mints `.completed/step-3` on every wrapper exit when it is absent, including apply-pending / vote-required bail-outs that never called `step3_loop_write_completed_step3()`. After the wrapper exits, the sentinel pair no longer signals mid-loop bail; an orchestrator that gates only on `[ -f …/step-3 ]` (without also honoring `STEP3_REVIEW_LOOP_STATUS`) can advance toward Step 3b on a non-terminal handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-contract-output.txt: Narrow the trap so it writes `step-3` only on terminal loop statuses (or when the loop already wrote `step-3`), and keep `step-3-terminal` gated on the current-pass persist sidecar as today; add a harness case for a `main-agent-apply-required` exit that asserts `step-3-terminal` exists but `step-3` stays absent until a real terminal completion.


### FINDING_12: marker_step_completed releases guard without persist sidecar check
- **Reviewer(s)**: dyn-guard-whitelist-output.txt
- **Severity**: blocking
- **Concern**: `marker_step_completed` for `design-step3-review` releases the live poll guard on `.completed/step-3-terminal` existence alone, but does not require the current-pass durability sidecar `.step3-terminal-persisted-this-run`. While a marker is live, the hook still allows unguarded Bash writes (`touch`, `: >`, `echo >`, `mkdir`) because `_PROBE_VERB_RE` omits write primitives and only `Read|Bash` are hooked. An orchestrator can forge `.completed/step-3-terminal`, drop the guard, then Read stale or partial `.step3-review-result.env` and other tmpdir progress artifacts before the background wrapper finishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-guard-whitelist-output.txt: In `marker_step_completed` for `design-step3-review`, require both a regular non-symlink `.completed/step-3-terminal` and a readable regular non-symlink `.step3-terminal-persisted-this-run` in the same marker dir before returning success; add hook denials (and harness tests) for Bash commands that create or truncate terminal sentinel paths under a live marker; consider extending the PreToolUse surface to `Write` for those paths.


### FINDING_13: foreground probe does not bind DESIGN_TMPDIR to live marker directory
- **Reviewer(s)**: dyn-guard-whitelist-output.txt
- **Severity**: blocking
- **Concern**: `bash_is_terminal_sentinel_foreground_probe` is syntax-only and does not bind `$DESIGN_TMPDIR` to the live marker directory from `live_dirs_file`. A foreground probe is allowed even when `DESIGN_TMPDIR=<other-path>` while a live marker blocks the real session tmpdir. Combined with forgeable terminal-sentinel release, the whitelist over-trusts sentinel presence as a security boundary rather than wrapper-proven durability, while docs treat `step-3-terminal` as authorization to parse `.step3-review-result.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-guard-whitelist-output.txt: When `live_dirs_file` is non-empty, allow the foreground probe only if the command's `DESIGN_TMPDIR` assignment (when present) equals a listed live dir, or `$DESIGN_TMPDIR` is unset and exactly one live dir exists; pair terminal-sentinel release in `marker_step_completed` with the persist sidecar check above so probe DONE and guard release share the same integrity predicate.


### FINDING_4: foreground probe echo tail allows command substitution and arbitrary shell syntax
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: blocking
- **Concern**: The foreground sentinel-probe allowlist is too permissive on the echo tail (and related prefix syntax). It accepts command substitutions and arbitrary shell syntax inside echo operands, then exits before generic probe-denial checks. With a live marker and absent `step-3-terminal`, probes such as `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo $(find${IFS}"$DESIGN_TMPDIR")` or `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo $(cat<"$DESIGN_TMPDIR"/.step3-review-result*)` can match the allow regex while still executing tmpdir or result-env reads when the sentinel is absent, reopening the progress-artifact polling hole the guard is meant to close.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Restrict the tail to exact static echo tokens such as `&& echo DONE || echo WAIT`, or reject command substitution and shell metacharacters in echo operands.
  - From codex-specialist-edge-cases-output.txt: Restrict the prefix to a safe absolute path that resolves to one of the live marker dirs, and restrict the echo tail to fixed safe literals such as `&& echo DONE || echo WAIT`; reject `$`, backticks, redirections, parentheses, and probe verbs anywhere outside the single allowed `test -f` / `[ -f ]`.
  - From codex-specialist-testing-output.txt: Restrict echo tails to exact safe literals and add command-substitution regression tests.


### FINDING_5: step2b drafter accepts empty DESIGN_TMPDIR
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Step 2b drafter port does not explicitly reject empty `DESIGN_TMPDIR`; `Path("")` becomes the current directory. If the repo has matching sentinel files, running the drafter with missing session env can write `.completed` and drafter artifacts into the repo instead of a design tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Check that `DESIGN_TMPDIR` is non-empty and passes `validate_design_tmpdir()` before sentinel validation or writes.


### FINDING_6: foreground probe uses naive control-flow substring guards
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The foreground probe matcher uses naive `*for*` / `*sleep*` / `*while*` / `*until*` substring checks on the full command. A probe with `DESIGN_TMPDIR=/tmp/informal-design` is denied because `informal` contains `for`, blocking sanctioned recovery on plausible paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use word-boundary control-flow detection (like bash_is_control_loop) instead of substring guards


### FINDING_8: prelaunch failure writes result env without terminal sentinel
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Prelaunch failure exits after `design_bg_wait_marker_start` write `.step3-review-result.env` through `lib-step3-prelaunch-failure.sh`, but they never create `.completed/step-3-terminal` or `.step3-terminal-persisted-this-run`. After a premature notification on `monitor-mode-unavailable` or `scope-anchor-missing`, the documented recovery probe can only return `WAIT`, even though the result envelope is durable and the wrapper is terminal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: After `_step3_review_write_result_env` successfully moves the result env on these current-pass terminal paths, write the same terminal sentinel and sidecar used by `step3_loop_write_terminal_step3`, or install the full cleanup trap before these prelaunch checks and make it key off a current-pass write sidecar.


### FINDING_9: step2a_main accepts empty or unvalidated DESIGN_TMPDIR
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `step2a_main` uses `Path(os.environ.get("DESIGN_TMPDIR", ""))` without requiring or validating an absolute design tmpdir, unlike `step2b_postplan_main`. If launcher env rehydration fails or `DESIGN_TMPDIR` is empty, Step 2a can write `.completed/` and sentinel artifacts under the current working directory, potentially the repository root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Fail closed when `DESIGN_TMPDIR` is missing, call `validate_design_tmpdir`, resolve it, and write the normalized value back to `os.environ` before any Step 2a reads or writes.
  - From codex-specialist-testing-output.txt: Fail closed on missing or invalid DESIGN_TMPDIR before any Step 2a reads or writes, and add a no-DESIGN_TMPDIR regression test.


