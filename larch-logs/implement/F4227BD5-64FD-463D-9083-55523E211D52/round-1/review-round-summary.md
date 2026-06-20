# Review Round 1

- Mode: `diff`
- 9 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Pause path writes premature step-5c-terminal sentinel
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-publish-rcs-output.txt
- **Severity**: important
- **Concern**: The outer `finally` in `step5c_core` writes `.completed/step-5c-terminal` whenever `design_tmpdir` is set, including on pause-save and other pre-publish early returns. That diverges from the retired Bash wrapper, which never wrote the terminal sentinel on pause. A pause can exit `0` with `PAUSE_OK` and no `PUBLISH_RC` rows while the sentinel exists, so background recovery that keys only on `step-5c-terminal` may treat publish as complete and parse an incomplete handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Skip terminal sentinel on the pause-save return path; reserve it for publish-tail completion and abort paths only.
  - From cursor-specialist-edge-cases-output.txt: Limit terminal writes to publish-entered paths and publish-tail abort staging; skip pause and pre-publish validation early returns.
  - From dyn-publish-rcs-output.txt: Skip the `finally` terminal write on the pause-return path (and other pre-publish early exits if they should not signal publish completion). Only write `.completed/step-5c-terminal` after publish work runs or on explicit publish-tail abort handling.


### FINDING_2: Render failure can emit stale final-summary markers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Render failures are swallowed and marked summary emission still runs if any stale `final-summary.md` is non-empty. `render_final_summary_main` can fail while an old `final-summary.md` remains, and the orchestrator may receive wrong `LARCH_FINAL_SUMMARY` markers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Gate `_emit_final_summary_marked_from_disk` on render success or a freshly written summary file.


### FINDING_3: Cleanup-eligibility matrix tests incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-harness-scope-output.txt
- **Severity**: important
- **Concern**: Plan-listed cleanup-eligibility cases are only partly covered. `CLEANUP_ELIGIBLE` logic for non-empty `SESSION_ID` with `PUBLISH_OK=true` (eligible) and non-empty `SESSION_ID` with `PUBLISH_OK=false` (ineligible) is untested. Step 6 cleanup behavior could regress without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the two missing cleanup matrix tests from the plan.
  - From cursor-specialist-testing-output.txt: Add pytest with SESSION_ID set, PLAN_WRITE_OK=true, publish_ok empty/false; assert CLEANUP_ELIGIBLE=false.
  - From dyn-harness-scope-output.txt: Add focused pytest cases: (2) parametrize cleanup eligibility over `SESSION_ID` × `PUBLISH_OK`.


### FINDING_4: Missing abort and absent-summary pytest coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-harness-scope-output.txt
- **Severity**: important
- **Concern**: Plan-required tests for unexpected publish abort (e.g. rc 5 or 9) and rc 0 render when `final-summary.md` is absent are missing; only rc 2 abort is covered. Abort staging and absent-summary render paths could break without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest cases for rc 5 abort staging and render-on-absent-summary success.
  - From dyn-harness-scope-output.txt: Add focused pytest cases: (1) success path where `fake_render` creates `final-summary.md` and assert markers; (3) one abort test with `publish_core` returning `5` or `9`, asserting `failed-publish-tail` staging, terminal sentinel, and captured `design-stage-terminal-state.{stdout,stderr}.log` files per `python/design_lifecycle.py:3555-3585`.


### FINDING_6: Subprocess stdout leaks past `redirect_stdout` capture
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Step 5c uses `contextlib.redirect_stdout` to capture `publish_core`, but child subprocess stdout from `python/design_publish.py:287-302` is not captured. A successful named-block write can emit `WRITTEN`/`MODE`/`MARKERS_PRESENT`/`BODY_BYTES` directly into Step 5c task output before `PUBLISH_RC=0`, violating the Step 5c stdout contract that used to receive only parsed rows after Bash redirected the whole publish subprocess.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Capture fd-level stdout/fd3 around publish_core, or capture publish-tail subprocess output and append only intended rows to the temp stdout file.
  - From codex-specialist-edge-cases-output.txt: Capture publish stdout at the file-descriptor level around publish_core, including child process stdout, or capture stdout for every publish-tail subprocess that may emit rows.
  - From cursor-specialist-testing-output.txt: Capture publish_core with fd-level stdout redirection or capture all publish-tail subprocess stdout explicitly, and add a regression test with a fake named-block write that prints stdout.
  - From codex-specialist-testing-output.txt: Capture publish_core with fd-level stdout redirection or capture all publish-tail subprocess stdout explicitly, and add a regression test with a fake named-block write that prints stdout.


### FINDING_7: Pause early return lacks Step 5c orchestrator stop contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Pause early-return lacks a Step 5c-specific orchestrator stop contract while a terminal sentinel may still be written (see FINDING_1). Background Step 5c can finish with exit 0 and `PAUSE_OK` output but without publish handoff rows, inviting the orchestrator to continue toward Step 5c items 5-7 instead of stopping for resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align with Step 2b PAUSE_OK halt semantics in SKILL.md and/or emit an explicit STEP5C_STATUS machine row; pair with gated terminal writes.


### FINDING_8: Lint harness still pins old Step 5c SKILL prose
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-cost-line-callsites.sh` still greps for old Step 5c design publish SKILL prose after SKILL.md was updated to design step5c. `make lint` runs this harness via test-harnesses-18 and can fail even when step5c unit tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update the grep pin to design step5c and route design SKILL.md edits to test-render-cost-line-callsites in checks.py direct-target rules.


### FINDING_10: Inherited-quiet test disables quiet instead of exercising it
- **Reviewer(s)**: dyn-harness-scope-output.txt
- **Severity**: important
- **Concern**: `test_step5c_main_machine_rows_visible_under_inherited_quiet` sets `LARCH_QUIET_DISABLE=1`, so `quiet_init` returns immediately and never establishes fd-3 contract routing. Assertions use `capsys.readouterr().out` (fd 1), which would miss contract-stream output when quiet is active. The test name claims inherited-quiet coverage but would not catch regressions where Step 5c machine rows are swallowed under a parent quiet session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-scope-output.txt: Mirror `test_capture_contract_stream_restores_fd3_for_quiet_init` (`python/test_design_lifecycle.py:1711-1736`) or `test_step_final_summary_cli_subprocess_emits_markers_on_stdout` (`python/test_design_lifecycle.py:1955-1982`): set `LARCH_QUIET_ACTIVE=1` with a foreign `LARCH_QUIET_PID`, omit `LARCH_QUIET_DISABLE`, invoke via `cli.main(["design", "step5c", ...])` or read fd 3 after `step5c_main`, and assert `PUBLISH_RC=0` (and marker rows) on the contract stream.


### FINDING_11: Abort staging test omits capture-log contract
- **Reviewer(s)**: dyn-harness-scope-output.txt
- **Severity**: important
- **Concern**: `test_step5c_core_publish_tail_abort_stages_renders_and_writes_terminal` checks terminal-state env and markers but not the `_capture_contract_stream_to_paths` log contract the plan requires to match the clarify hard-halt pattern. A staging regression that still writes `design-failure-terminal-state.env` but drops or corrupts capture logs would pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-scope-output.txt: Assert `(design / "design-stage-terminal-state.stdout.log").is_file()` and `.stderr.log` exist and are non-empty on rc `2` abort; optionally assert `_append_failure` warnings when `STAGED=false` or staging rc is non-zero.


