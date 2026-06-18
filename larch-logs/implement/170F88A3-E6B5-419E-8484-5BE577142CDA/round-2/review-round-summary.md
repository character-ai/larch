# Review Round 2

- Mode: `diff`
- 6 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_11: test_preflight.py missing footer-false-positive regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `scripts/test-implement-preflight.sh` tested that illustrative `rounds_completed: 0` prose in the plan body does not refuse when footer metadata has `rounds_completed: 2`. New Python scan in `preflight.py` has no equivalent pytest. Footer-scan regression could falsely refuse valid reviewed plans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a stubbed plan-block test with body prose containing `rounds_completed: 0` and footer `rounds_completed: 2`; assert preflight_main returns 0.


### FINDING_12: test_preflight.py missing malformed rounds_completed refusal test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted Bash harness covered non-numeric `rounds_completed` (e.g. `nope`); `preflight.py` refuses at lines 267-271 but `test_preflight.py` does not exercise that branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a test with footer `rounds_completed: nope`; assert exit 2 and the malformed-metadata refusal string.


### FINDING_13: test_closeout.py Slack skip path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan required Slack skip/fail coverage; deleted `test-step-16-17.sh` asserted `STATUS=skipped` does not append Warnings, but `test_closeout.py` only tests `STATUS=failed`. Regression could log spurious Warnings on the common skipped-webhook path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `test_step_16_17_slack_skipped_no_warnings` with `slack_status=skipped` and assert execution-issues.md is absent.


### FINDING_17: closeout.py stale-summary guard bypass when backup move fails
- **Reviewer(s)**: dyn-closeout-flow-output.txt
- **Severity**: important
- **Concern**: The `--no-print-stdout` stale-summary guard can be bypassed when moving `summary-final.md` to `.summary-final.pre-step17.bak` fails. On `OSError`, `had_backup` stays `false` but the old file remains. If `final-report write` then fails before overwriting it, `_summary_nonempty(tmpdir)` is still true and `step_17` returns `0`. `step_16_17` treats that as success and emits markers from stale content. Retired Bash used `set -e` on `mv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-closeout-flow-output.txt: Treat a failed backup move as a hard failure (return non-zero immediately), or only allow the failure-path `return 0` when `had_backup` is true. Optionally restore from backup when the write fails and the on-disk summary was not produced in this invocation.


### FINDING_18: closeout.py ignores _print_summary_markers return value
- **Reviewer(s)**: dyn-closeout-flow-output.txt
- **Severity**: important
- **Concern**: `step_16_17` ignores the return value of `_print_summary_markers`. If `summary-final.md` read or `.step17-printed` touch fails after `---LARCH-SUMMARY-FINAL-BEGIN---` is printed, stdout can contain a partial marker pair while `.step17-printed` is never created. Orchestrator may emit an incomplete summary; Step 18 `.step17-emitted` gating can disagree with what was printed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-closeout-flow-output.txt: Check `_print_summary_markers` return code; on failure, avoid leaving a partial pair on stdout (buffer and print atomically, or print a single error line), and do not treat closeout as having printed markers.


### FINDING_6: closeout.py missing fail-closed CLAUDE_PLUGIN_ROOT validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Python closeout dropped fail-closed `CLAUDE_PLUGIN_ROOT` validation present in retired `step-16-17.sh`. Stale `plugin-root.env` or bad `CLAUDE_PLUGIN_ROOT` makes Step 16/17 subprocesses fail silently while `step_16_17` still returns `0`; orchestrator may miss summary markers and only see best-effort child failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After `_plugin_root()` verify `plugin_root.is_dir()` and `(plugin_root / python/cli.py).is_file()`; stderr + return 2 before subprocesses (mirror preflight.py).


