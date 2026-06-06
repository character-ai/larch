### [rejected] FINDING_1

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_1: **No production redaction or publication logic changes.** `scripts/larch-log.sh` edits are comment-only; `round_artifact_included()` behavior is unchanged. D1 adds regression fixtures asserting static Codex `.json`/`.cap-hit` sidecars stay excluded — a coverage improvement, not a new exposure path.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No production redaction or publication logic changes.** `scripts/larch-log.sh` edits are comment-only; `round_artifact_included()` behavior is unchanged. D1 adds regression fixtures asserting static Codex `.json`/`.cap-hit` sidecars stay excluded — a coverage improvement, not a new exposure path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: scripts/test-implement-structure.sh:617-618
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] A3 HARD/SIMPLE regex can match non-workflow prose in Step 2 dispatch files. Future comment or fixture text containing SIMPLE or HARD as standalone tokens fails the harness despite no workflow branching. Assert specific legacy workflow tokens/paths instead of bare tier words.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: `2733f0a86` — Implement OOS housekeeping batch
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `2733f0a86` — Implement OOS housekeeping batch
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: `68d7ed4bc` — chore(larch-logs) flush (intentional run-log artifact; not reviewed as scope drift)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `68d7ed4bc` — chore(larch-logs) flush (intentional run-log artifact; not reviewed as scope drift) The implementation commit matches the plan: A1/A3 harness extensions, A2 timing-skill pins on five launchers, B monitor-level tests, C no-op (already fixed upstream), D1–D4 test/doc/comment updates. No production logic changes beyond telemetry env prefixes on existing `record-vendor-task` lines. ### Plan / acceptance traceability | Item | Status | |------|--------| | **A1** — awk scanner + retained literal greps | Present in `scripts/test-implement-structure.sh` | | **A2** — five launcher pins (`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement`) | Present; `launch-review.sh` untouched per plan | | **A3** — workflow-free Step 2 + `workflow_path` deny | Present | | **B** — `already_merged → Outcome.OK`, consecutive errors → `Outcome.TRANSIENT` | Two focused tests in `python/test_ci_monitor.py` | | **C** — verify-only | No diff (expected) | | **D1** — static Codex `.json` / `.cap-hit` exclusion fixtures | Present | | **D2/D3/D4** — comment/doc-only | Present across `larch-log.sh`, `SECURITY.md`, quiet-log docs | CI wiring is unchanged but sufficient: `test-implement-structure` and `test-larch-log-write-round` are already in `Makefile` harness buckets; `test_ci_monitor.py` is covered by `py-test`. ### Testing / regression assessment
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **A1 scanner** correctly uses basename matching, same-line pin checks, and excludes comment-only `timing-ledger.sh` references (requires ` mark ` / `record-vendor-task`). Multi-line `record-vendor-task` continuations are safe because only the first line carries `timing-ledger.sh`.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **A1 scanner** correctly uses basename matching, same-line pin checks, and excludes comment-only `timing-ledger.sh` references (requires ` mark ` / `record-vendor-task`). Multi-line `record-vendor-task` continuations are safe because only the first line carries `timing-ledger.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **A2** is statically enforced by the new scanner; runtime polluted-env attribution is not exercised, which aligns with the plan’s static-only acceptance.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **A2** is statically enforced by the new scanner; runtime polluted-env attribution is not exercised, which aligns with the plan’s static-only acceptance.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **B** tests fill a real gap: `test_poll_ci_three_consecutive_errors_bail` covers `poll_ci`; the new `test_monitor_*` cases cover `monitor()` outcome mapping (`Outcome.OK` for `already_merged`, `Outcome.TRANSIENT` with `"3 times consecutively"` detail). The `gh pr view` rc=1 stub path matches `gather_status` → three consecutive failures → transient classification via `retry.is_transient_net_signature`.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **B** tests fill a real gap: `test_poll_ci_three_consecutive_errors_bail` covers `poll_ci`; the new `test_monitor_*` cases cover `monitor()` outcome mapping (`Outcome.OK` for `already_merged`, `Outcome.TRANSIENT` with `"3 times consecutively"` detail). The `gh pr view` rc=1 stub path matches `gather_status` → three consecutive failures → transient classification via `retry.is_transient_net_signature`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **D1** fixtures hit the existing deny clause at `scripts/larch-log.sh:74`; assertions mirror adjacent static-Codex exclusions.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **D1** fixtures hit the existing deny clause at `scripts/larch-log.sh:74`; assertions mirror adjacent static-Codex exclusions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_2: **`SECURITY.md` changes improve disclosure rather than weaken controls.** The softened “safe without scanner” wording now limits the claim to covered secret-shaped families and explicitly calls out operator discipline for unmatched secrets/PII. The new dynamic-Codex paragraph (lines 290–295) documents by-design residual risk under pattern-based scrubbing, matching the D4 plan intent.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`SECURITY.md` changes improve disclosure rather than weaken controls.** The softened “safe without scanner” wording now limits the claim to covered secret-shaped families and explicitly calls out operator discipline for unmatched secrets/PII. The new dynamic-Codex paragraph (lines 290–295) documents by-design residual risk under pattern-based scrubbing, matching the D4 plan intent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Regression risk** is low: comment/doc edits, additive harness checks, env-prefix pins on timing calls, and two isolated unit tests.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **Regression risk** is low: comment/doc edits, additive harness checks, env-prefix pins on timing calls, and two isolated unit tests.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_3: **A2 launcher pins are telemetry-only.** `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` on `record-vendor-task` lines affects timing-ledger skill attribution under polluted shells. It does not change auth, argv construction, prompt handling, or run-log flush/redaction paths. `launch-review.sh` remains correctly excluded.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **A2 launcher pins are telemetry-only.** `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` on `record-vendor-task` lines affects timing-ledger skill attribution under polluted shells. It does not change auth, argv construction, prompt handling, or run-log flush/redaction paths. `launch-review.sh` remains correctly excluded.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: **D3 documents pre-existing append behavior.** `python/logging_util.py` adds a comment only; default quiet-log paths include PID, so cross-process accumulation requires an explicit `LARCH_QUIET_LOG_FILE` pin — now documented as an intentional forensics tradeoff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **D3 documents pre-existing append behavior.** `python/logging_util.py` adds a comment only; default quiet-log paths include PID, so cross-process accumulation requires an explicit `LARCH_QUIET_LOG_FILE` pin — now documented as an intentional forensics tradeoff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: **Tests use dummy/synthetic data.** New write-round fixtures are clearly labeled excluded content. `test_ci_monitor.py` additions use `RecordingRunner` stubs with no real `gh`/`git` I/O.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests use dummy/synthetic data.** New write-round fixtures are clearly labeled excluded content. `test_ci_monitor.py` additions use `RecordingRunner` stubs with no real `gh`/`git` I/O.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: **A1/A3 harness additions** scan a fixed production script set in CI only; no untrusted input flows into shell execution.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **A1/A3 harness additions** scan a fixed production script set in CI only; no untrusted input flows into shell execution. No injection, auth boundary, secret-handling, path-traversal, or crypto regressions were introduced or amplified by this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: correctness: scripts/test-implement-structure.sh:574-590
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Scanner omits implement-reachable shared vendor timing emitters, leaving A1/A2 incomplete despite the harness passing. With LARCH_TIMING_SKILL=design in the environment, implement lint-fix Codex rows via scripts/launch-codex-exec.sh:211 and Step 7a Claude code-flow rows via scripts/launch-claude-subprocess.sh:237 are recorded as design and ignored by implement timing reports. Pin DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement at the implement call sites or add an explicit launcher skill override, then extend the harness to cover those paths without mis-tagging review callers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: architecture: scripts/test-implement-structure.sh:605-607
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] A3 uses substring grep for workflow_path across 15 production emitter scripts. A harmless comment or doc string mentioning workflow_path in any scanned file breaks CI without a behavioral regression. Restrict checks to actual run-params reads or exclude comment-only matches.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

