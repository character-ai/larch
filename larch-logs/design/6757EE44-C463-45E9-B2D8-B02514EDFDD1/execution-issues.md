### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	blocking	requirements	plan.txt	Plan artifact unreadable in reviewer session; completeness against binding issue scope not verified	Binding scope requires picking a precision-value metric before token-allocation code ships, updating docs/point-competition.md and skills/shared/voting-protocol.md, identifying token-allocation implementation surfaces, and honoring value-weighted points plus voter-calibration dependencies; this slot cannot confirm the plan covers those items	Re-run Requirements review after plan.txt is readable

1. **requirements** | `plan.txt` | Plan artifact unreadable in reviewer session; completeness against binding issue scope not verified | Binding scope requires metric selection before allocation code, doc updates on `docs/point-competition.md` and `skills/shared/voting-protocol.md`, token-allocation surface coverage, and explicit dependency handling for value-weighted points and voter calibration; none of that could be checked against `plan.txt` in this session | Re-run the Requirements slot once the plan file is accessible to the reviewer toolchain
## Reviewer stderr (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/cursor-plan-requirements-output.txt.launch-stderr)

❌ cursor agent: FAILED (exit code 1, output 0 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
✓ cursor agent: completed (exit code 0, output 1517 bytes)
  ```
