### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 20s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

Failed with exit code 1 after 20s. Output size: 0 bytes.

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

Reading additional input from stdin...
2026-05-30T22:20:50.399803Z ERROR codex_core::session: failed to record rollout items: thread 019e7af9-bae1-7d21-b583-af423689a57f not found
❌ codex agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)

## Launcher stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

(empty: <TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 20s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

{"no_issues_found": true}


## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

Failed with exit code 1 after 20s. Output size: 0 bytes.

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

Reading additional input from stdin...
2026-05-30T22:20:52.520310Z ERROR codex_core::session: failed to record rollout items: thread 019e7af9-bbc7-7d03-8a0b-7d8ca7132ee0 not found
❌ codex agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)

## Launcher stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

(empty: <TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 20s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	plan.txt:27-28; scripts/lib-validate-meta-path.sh:14-25; scripts/test-launch-review.sh:1871-1878	launch-review --stderr-sink validation says reject .. but reuse validate_meta_scalar_path which only checks the charset allowlist (same as run-external-agent --stderr-sink and launch-review --output)	test-launch-review.sh extension pins .. rejection at parse time; implementer following validate_meta_scalar_path only passes newline tests and .. reaches .meta / retry	Align the plan and harness: either drop .. from launch-review parse-time rejection (keep .. fail-closed in validate_retry_stderr_sink_or_mark only, matching --output) or add an explicit *..* guard beside validate_meta_scalar_path and pin exact message + exit code
2	in_scope	important	correctness	plan.txt:27; scripts/test-launch-review.sh:1877-1878; scripts/launch-review.sh:149	Plan requires exit 2 for bad --stderr-sink; launch-review uses exit 1 for validate_meta_scalar_path failures on --output	Harness pins exit 1 + ERROR: prefix for --output; stderr-sink validation diverges and tests fight the launcher argv contract	Match --output: validate_meta_scalar_path --stderr-sink ... || exit 1; update the test plan to pin exit 1 and the lib error text unless there is a deliberate reason to treat this flag differently
3	in_scope	nit	architecture	plan.txt:23-30; scripts/launch-review.sh:529-542,954-966	Full inner threading of --stderr-sink into every run-external-agent call is inert for current codex/cursor capture modes and no production caller passes the flag yet	~15-25 extra launch-review lines + dual-branch parity tests for zero present-day stderr-tail benefit on review lanes	Minimum-change alternative: parse --stderr-sink (avoid exit 2 on collector forward) and record it in outer .meta only; defer inner _RUN_EXTERNAL_SINK_ARGS wiring until a launch-review lane actually redirects fd2 to that sink

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

Failed with exit code 1 after 20s. Output size: 0 bytes.

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

Reading additional input from stdin...
2026-05-30T22:20:55.409560Z ERROR codex_core::session: failed to record rollout items: thread 019e7af9-b798-7af3-a575-ec2aac860bed not found
❌ codex agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)

## Launcher stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

(empty: <TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 20s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

Failed with exit code 1 after 20s. Output size: 0 bytes.

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.stderr-tail)

Reading additional input from stdin...
2026-05-30T22:20:58.403720Z ERROR codex_core::session: failed to record rollout items: thread 019e7af9-c566-75f0-903c-347ebff370d0 not found
❌ codex agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)

## Launcher stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

(empty: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

  ```

- **Step design Step 3 — plan-review-loop.sh (operator-aborted) failed (exit 143)**:
  ```
Step 3 plan-review panel aborted by operator at user request.
Root cause: codex agents failed repeatedly with 'ERROR codex_core::session: failed to record rollout items: thread <id> not found' (exit 1, 0 bytes), and the panel waterfall kept retrying — the 'runs for many hours' bug.
Outcome: no usable findings (voting-tally.md / accepted-plan-findings.md / rejected-findings.md / oos.md all empty); plan.txt proceeds unchanged.
--- task output tail (codex failures) ---
❌ codex agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)
--- end failed agent stderr tail ---
--- failed agent stderr tail ---
Reading additional input from stdin...
2026-05-30T22:20:55.409560Z ERROR codex_core::session: failed to record rollout items: thread 019e7af9-b798-7af3-a575-ec2aac860bed not found
❌ codex agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)
--- end failed agent stderr tail ---
--- failed agent stderr tail ---
Reading additional input from stdin...
2026-05-30T22:20:58.403720Z ERROR codex_core::session: failed to record rollout items: thread 019e7af9-c566-75f0-903c-347ebff370d0 not found
❌ codex agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)
--- end failed agent stderr tail ---
  ```
