# Review Round 4

- Mode: `diff`
- 10 accepted, 17 rejected (8 exonerated)

## Accepted Findings

### FINDING_19: architecture: skills/design/scripts/design-plan-quality-assessor.md:36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Responsibility text documents rollback order and no-decrement-on-write-cursor-failure that contradict implementation and test 21. Operators or future edits may "fix" rollback to match the doc and break harness/test-run-step3-review round-count semantics. Update item 7 to decrement-then-write-cursor; document WARN-on-write-cursor-fail without count restore.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/design/scripts/design-plan-quality-assessor.sh:310-314
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit-0 assess path defaults empty KVs to skipped rather than assess-failed. Truncated or buggy assess stdout after successful write-after proceeds with no quality gate and no execution-issues capture. Fail closed when ASSESSOR_STATUS is empty after assess rc=0; log capture and set assess-failed.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/design/SKILL.md:1100-1102
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _assessor_parse_ok flips true on any routing key not ASSESSOR_STATUS. Partial corrupt .step3.6-assessor.env can suppress stdout WARN replay while mandatory-key guard still aborts late. Set parse_ok only when ASSESSOR_STATUS is populated from file or treat partial parse as stdout fallback.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/design/scripts/test-design-plan-quality-assessor.sh:615-625
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness lacks handoff chat assertion for read-cursor failure WARN. File-parse WARN replay for read-cursor could regress without failing CI. Add apply_step3_6_handoff case asserting read-cursor WARN in chat.out.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/design/SKILL.md:1055-1067
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Orchestrator pre-read aligns workflow_path to design_classification when they disagree; plan required same-as-inline workflow_path pre-read and behavior preservation. Stale run-params with workflow_path=SIMPLE and design_classification=HARD previously skipped Step 3.6; now prints HARD banner and runs snapshot/assessor work. Remove _dc override from orchestrator pre-read or amend plan and add harness coverage for disagreeing fields.
- **Suggested revision**: Address the concern above.


### FINDING_26: **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:197-210,237-250,286-300` — On the degraded paths that must always settle at exit `0` (`read-cursor` logging, `write-after-failed`, and `assess-failed`), housekeeping steps (`mktemp`, `printf` into the temp capture file, `rm -f "$_cap"`, and `printf` into `review-round-count.txt`) run under the script-wide `set -euo pipefail` without a local `set +e` guard. Any of those failing aborts the driver before `_write_result_and_emit`, producing exit `1` instead of the contracted settled `0`, leaving no `.step3.6-assessor.env`, and forcing the Step 3.6 orchestrator down the mandatory-keys / catch-all abort paths. The removed inline `SKILL.md` lane did not run under `set -e`, so this is a regression on failure of ancillary I/O. **Suggested fix:** Wrap each degrade block’s non-contract housekeeping (`mktemp`, cap write, `rm`, count-file write) in `set +e` … `set -e` the same way child script calls are wrapped, or funnel it through a small helper that never aborts; guarantee `_write_result_and_emit` runs on every branch that sets `ASSESSOR_STATUS` to `write-after-failed`, `assess-failed`, or skip variants before `exit 0`.
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:197-210,237-250,286-300` — On the degraded paths that must always settle at exit `0` (`read-cursor` logging, `write-after-failed`, and `assess-failed`), housekeeping steps (`mktemp`, `printf` into the temp capture file, `rm -f "$_cap"`, and `printf` into `review-round-count.txt`) run under the script-wide `set -euo pipefail` without a local `set +e` guard. Any of those failing aborts the driver before `_write_result_and_emit`, producing exit `1` instead of the contracted settled `0`, leaving no `.step3.6-assessor.env`, and forcing the Step 3.6 orchestrator down the mandatory-keys / catch-all abort paths. The removed inline `SKILL.md` lane did not run under `set -e`, so this is a regression on failure of ancillary I/O. **Suggested fix:** Wrap each degrade block’s non-contract housekeeping (`mktemp`, cap write, `rm`, count-file write) in `set +e` … `set -e` the same way child script calls are wrapped, or funnel it through a small helper that never aborts; guarantee `_write_result_and_emit` runs on every branch that sets `ASSESSOR_STATUS` to `write-after-failed`, `assess-failed`, or skip variants before `exit 0`.
- **Suggested revision**: Address the concern above.


### FINDING_28: **correctness** `skills/design/scripts/test-design-plan-quality-assessor.sh:207-273` — `apply_step3_6_handoff` turns errexit off with `set +e` for driver capture but never restores `set -e` before `return`. Because `set +/-e` is shell-global, callers that invoke the mirror without their own trailing `set -e` (or that add assertions after the call inside the same subshell) run subsequent checks with errexit disabled, weakening fail-closed coverage of the handoff abort guards the harness is meant to pin. **Suggested fix:** Add `set -e` immediately before each `return` in `apply_step3_6_handoff` (after the abort checks, which intentionally need `set +e` or explicit rc tests), matching the `SKILL.md` fence pattern at `skills/design/SKILL.md:1073-1079`.
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-design-plan-quality-assessor.sh:207-273` — `apply_step3_6_handoff` turns errexit off with `set +e` for driver capture but never restores `set -e` before `return`. Because `set +/-e` is shell-global, callers that invoke the mirror without their own trailing `set -e` (or that add assertions after the call inside the same subshell) run subsequent checks with errexit disabled, weakening fail-closed coverage of the handoff abort guards the harness is meant to pin. **Suggested fix:** Add `set -e` immediately before each `return` in `apply_step3_6_handoff` (after the abort checks, which intentionally need `set +e` or explicit rc tests), matching the `SKILL.md` fence pattern at `skills/design/SKILL.md:1073-1079`.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: skills/design/scripts/design-plan-quality-assessor.md:36
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Responsibility bullet 7 documents rollback order opposite to implementation. Future edits may reorder rollback and break harness expectations (count 1, cursor 2 after round-2 write-after failure). Update item 7 to: decrement review-round-count.txt then best-effort write-cursor --value ROUND_NUM.
- **Suggested revision**: Address the concern above.


### FINDING_6: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test for workflow_path vs design_classification mismatch WARN and chat replay. Operator-visible disagreement breadcrumb could regress while driver still runs HARD lane. Add run-params conflict fixture; assert WARN in result env and apply_step3_6_handoff chat.out.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:557-593
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Immutable env tests hard-fail when chflags/chattr unavailable. Linux CI may report harness failure unrelated to product logic. Skip with explicit pass or use a portable write-failure injection.
- **Suggested revision**: Address the concern above.


