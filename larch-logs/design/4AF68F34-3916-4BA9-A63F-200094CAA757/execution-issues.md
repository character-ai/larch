### External Reviewer Issues

- **Step design Step 3 — run-step3-review.sh (LOOP_STATUS=panel-failed) failed (exit 1)**:
  ```
Step 3 plan-review panel returned LOOP_STATUS=panel-failed.
Root cause: run-step3-review.sh forwards --convergence-threshold to plan-review-loop.sh,
which rejects unknown options (exit 2). This is the SAME regression (#3265/#3269) that
Workstream B of this very design (#3274) removes end-to-end. On the installed 47.0.19
plugin (byte-identical to repo HEAD for both scripts), Step 3 external plan review cannot
run until this fix lands. Design proceeds to Gate C with the unreviewed plan; once #3274
merges, /design Step 3 review works again.
  ```

- **Step design Step 3 — collect-agent-results.sh codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-harness-fidelity-output.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-harness-fidelity-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	<TMPDIR>/plan.txt:27-29; skills/cleanup/scripts/test-cleanup.sh:78-87; skills/cleanup/scripts/cleanup.sh:55-61,99-110	The proposed /tmp enumeration test can pass on the cache warning instead of proving the /tmp warning. run_cleanup always creates both the cache sessions dir and tmp root, and the planned stub fails every find containing -mindepth 1, which matches both top-level enumeration passes. Because the planned assertions only check generic failed to enumerate plus TMP_REMOVED=0, an implementation that warns for cache enumeration but still silently swallows /tmp enumeration failure would satisfy enumeration-failure-warns-tmp for the wrong reason.	Assert the exact pass-specific warning text for each new case, especially skipping /tmp cleanup for the tmp case, or make the enum-failure stub fail only for the target root per case so the warning source is unambiguous.
## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-harness-fidelity-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-harness-fidelity-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-dyn-harness-fidelity-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-dyn-harness-fidelity-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-dyn-harness-fidelity-output.txt.launch-stderr)

(empty: <TMPDIR>/codex-primary-plan-dyn-harness-fidelity-output.txt.launch-stderr)

  ```

### Warnings

- **Step dispatch-plan-voters.sh cursor — launch-review.sh --tool cursor (voter parse-rate check) warning (exit 0)**:
  ```
slot=3
voter_tool=cursor
judge_error_count=3
total_findings=3
total_ballot_items=3
voter_file=<TMPDIR>/cursor-vote-output.txt
voter_sha256=f020b4c5010a72e9ed7c8e3f953c8649325b7f386523d3dbf8ea1edaca8d9d9d
--- first 200 bytes of voter output ---
CURSOR_DEGRADED_RESPONSE

  ```
