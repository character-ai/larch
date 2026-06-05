### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: (plus merged upstream chores unrelated to this feature)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - (plus merged upstream chores unrelated to this feature) ## Plan verification (summary) The diff matches the stated intent:
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: `/implement` no longer passes `--workflow`, persists `WORKFLOW_PATH`, or calls `timing-ledger.sh workflow-path`; Step 2 timeout is fixed at 7200s.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `/implement` no longer passes `--workflow`, persists `WORKFLOW_PATH`, or calls `timing-ledger.sh workflow-path`; Step 2 timeout is fixed at 7200s.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: Implement summaries and timing reports omit Path / Workflow path; `timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design`; implement callers pin `LARCH_TIMING_SKILL=implement` and clear `DESIGN_TMPDIR`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Implement summaries and timing reports omit Path / Workflow path; `timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design`; implement callers pin `LARCH_TIMING_SKILL=implement` and clear `DESIGN_TMPDIR`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: `report_tokens_scan._workflow` early-returns `""` for implement; render/issue paths are skill-aware; design behavior is preserved behind explicit `LARCH_TIMING_SKILL=design` pins.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `report_tokens_scan._workflow` early-returns `""` for implement; render/issue paths are skill-aware; design behavior is preserved behind explicit `LARCH_TIMING_SKILL=design` pins.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: Round-1 gaps (legacy-flag test, `LARCH_TIMING_SKILL` pins on commit scripts, omit-`--workflow-path` render test, degraded-tools fence) appear addressed.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Round-1 gaps (legacy-flag test, `LARCH_TIMING_SKILL` pins on commit scripts, omit-`--workflow-path` render test, degraded-tools fence) appear addressed. Checked edge cases called out in the plan: polluted design env (shell + Python tests), legacy ledger `v1 workflow` rows, stale `WORKFLOW_PATH` / `POST_PLAN_WORKFLOW_PATH` in tmpdir artifacts, and implement cache NDJSON omitting `"workflow"`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **Env pollution**: Implement timing callers pin `LARCH_TIMING_SKILL=implement` and clear `DESIGN_TMPDIR` (`timing-report.sh`, `implement-finalize.sh`, `refresh-run-logs.sh`, `step-7a.sh`, `run-relevant-checks-captured.sh`, `step-telemetry-mark.sh`, `python/run_logs.py::_report_subprocess_env`). `timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design` only.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Env pollution**: Implement timing callers pin `LARCH_TIMING_SKILL=implement` and clear `DESIGN_TMPDIR` (`timing-report.sh`, `implement-finalize.sh`, `refresh-run-logs.sh`, `step-7a.sh`, `run-relevant-checks-captured.sh`, `step-telemetry-mark.sh`, `python/run_logs.py::_report_subprocess_env`). `timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design` only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **Reduced scan surface**: `python/report_tokens_scan.py::_workflow` returns `""` for implement before opening auxiliary JSON; `SECURITY.md` documents this boundary.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Reduced scan surface**: `python/report_tokens_scan.py::_workflow` returns `""` for implement before opening auxiliary JSON; `SECURITY.md` documents this boundary.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **Stale session data**: `write-final-report.sh` no longer reads `WORKFLOW_PATH` / `POST_PLAN_WORKFLOW_PATH`, so committed/session artifacts cannot repopulate the public Path bullet.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Stale session data**: `write-final-report.sh` no longer reads `WORKFLOW_PATH` / `POST_PLAN_WORKFLOW_PATH`, so committed/session artifacts cannot repopulate the public Path bullet.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Input validation**: `compute-pr-line-counts.sh` rejects non-numeric PR numbers and malformed repo slugs before `gh api`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Input validation**: `compute-pr-line-counts.sh` rejects non-numeric PR numbers and malformed repo slugs before `gh api`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/test-implement-structure.sh:2947-2955
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan acceptance requires all production timing callers to pin LARCH_TIMING_SKILL=implement, but enforcement is fragmented across multiple harnesses with no unified production-script grep. A new implement script can add timing-ledger.sh mark without the pin and pass CI until an operator notices missing Step N intervals after a /design→/implement session. Add one test-implement-structure block grepping an allowlisted production caller set for LARCH_TIMING_SKILL=implement (and DESIGN_TMPDIR clearing on timing-report calls).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Fail-safe degradation**: `degraded-tools-gate.sh` treats empty presence inputs as down when caller rehydration is incomplete.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fail-safe degradation**: `degraded-tools-gate.sh` treats empty presence inputs as down when caller rehydration is incomplete.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **Subprocess safety**: Timing refresh uses argv-array `subprocess.Popen` (no shell); ledger mark fields go through `sanitize_field`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Subprocess safety**: Timing refresh uses argv-array `subprocess.Popen` (no shell); ledger mark fields go through `sanitize_field`. No injection, auth bypass, secret leakage, path traversal, or deserialization regressions were found in the changed production paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_25: correctness: scripts/timing-report.sh:4171-4175
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Removing workflow row parsing and workflow_ts from last_event_ts changes duration math for legacy ledgers. Re-running timing-report.sh against an old implement ledger that still has v1 workflow rows can emit shorter total_seconds/total_hms than the committed timing-report.json from the original run. Document the behavior in timing-report.md or retain a legacy-only workflow_ts floor for implement re-renders while keeping workflow_path unknown in output.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: architecture: scripts/step-telemetry-mark.sh; skills/implement/SKILL.md:774,1177,1212,1300
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Steps 5/16/17/18 entry timing marks use a new helper not named in the plan file list. Plan/harness docs still describe inline timing-ledger pins; future edits may miss the helper contract. Add the helper to the plan acceptance grep or restore inline LARCH_TIMING_SKILL=implement fences per original plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: `37fed349b` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `37fed349b` — Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: `3c40c119b` — chore(larch-logs) implement run flush
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `3c40c119b` — chore(larch-logs) implement run flush
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: `7c00d697d` — Remove implement workflow classification
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `7c00d697d` — Remove implement workflow classification
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

