### External Reviewer Issues

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-3/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair REJECT structured TSV row: expected 8 tab columns, got 6 REJECT structured TSV: 1 data row(s) seen but none validated after salvage

## Reviewer output (<TMPDIR>/plan-review/round-3/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	risk-integration	plan.txt:77-89	The file list regenerates the canonical template and three generated reviewer agents, but it never names the two hand-maintained specialist prompts that still own live bodies: `agents/reviewer-testing.md` and `agents/reviewer-edge-cases.md`. `generate pre-rendered-reviewer-prompts` will keep snapshotting those files unchanged, so `/review` and `/implement` continue serving the old default-test-to-Out-of-Scope Necessity gate on those prompts after this PR. Add both hand-maintained files to the modify list, refresh their pre-rendered bodies and `.manifest`, and include them in the dependency-order regeneration step.
## Reviewer stderr (<TMPDIR>/plan-review/round-3/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/plan-review/round-3/codex-primary-plan-pragmatic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-3/codex-primary-plan-pragmatic-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-3/codex-primary-plan-pragmatic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-3/codex-primary-plan-pragmatic-output.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
✓ codex agent: completed (exit code 0, output 764 bytes)
  ```
