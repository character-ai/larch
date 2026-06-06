### FINDING_1: **No production redaction or publication logic changes.** `scripts/larch-log.sh` edits are comment-only; `round_artifact_included()` behavior is unchanged. D1 adds regression fixtures asserting static Codex `.json`/`.cap-hit` sidecars stay excluded — a coverage improvement, not a new exposure path.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No production redaction or publication logic changes.** `scripts/larch-log.sh` edits are comment-only; `round_artifact_included()` behavior is unchanged. D1 adds regression fixtures asserting static Codex `.json`/`.cap-hit` sidecars stay excluded — a coverage improvement, not a new exposure path.
- **Suggested revision**: Address the concern above.

### FINDING_2: **`SECURITY.md` changes improve disclosure rather than weaken controls.** The softened “safe without scanner” wording now limits the claim to covered secret-shaped families and explicitly calls out operator discipline for unmatched secrets/PII. The new dynamic-Codex paragraph (lines 290–295) documents by-design residual risk under pattern-based scrubbing, matching the D4 plan intent.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`SECURITY.md` changes improve disclosure rather than weaken controls.** The softened “safe without scanner” wording now limits the claim to covered secret-shaped families and explicitly calls out operator discipline for unmatched secrets/PII. The new dynamic-Codex paragraph (lines 290–295) documents by-design residual risk under pattern-based scrubbing, matching the D4 plan intent.
- **Suggested revision**: Address the concern above.

### FINDING_3: **A2 launcher pins are telemetry-only.** `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` on `record-vendor-task` lines affects timing-ledger skill attribution under polluted shells. It does not change auth, argv construction, prompt handling, or run-log flush/redaction paths. `launch-review.sh` remains correctly excluded.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **A2 launcher pins are telemetry-only.** `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` on `record-vendor-task` lines affects timing-ledger skill attribution under polluted shells. It does not change auth, argv construction, prompt handling, or run-log flush/redaction paths. `launch-review.sh` remains correctly excluded.
- **Suggested revision**: Address the concern above.

### FINDING_4: **D3 documents pre-existing append behavior.** `python/logging_util.py` adds a comment only; default quiet-log paths include PID, so cross-process accumulation requires an explicit `LARCH_QUIET_LOG_FILE` pin — now documented as an intentional forensics tradeoff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **D3 documents pre-existing append behavior.** `python/logging_util.py` adds a comment only; default quiet-log paths include PID, so cross-process accumulation requires an explicit `LARCH_QUIET_LOG_FILE` pin — now documented as an intentional forensics tradeoff.
- **Suggested revision**: Address the concern above.

### FINDING_5: **Tests use dummy/synthetic data.** New write-round fixtures are clearly labeled excluded content. `test_ci_monitor.py` additions use `RecordingRunner` stubs with no real `gh`/`git` I/O.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests use dummy/synthetic data.** New write-round fixtures are clearly labeled excluded content. `test_ci_monitor.py` additions use `RecordingRunner` stubs with no real `gh`/`git` I/O.
- **Suggested revision**: Address the concern above.

### FINDING_6: **A1/A3 harness additions** scan a fixed production script set in CI only; no untrusted input flows into shell execution.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **A1/A3 harness additions** scan a fixed production script set in CI only; no untrusted input flows into shell execution. No injection, auth boundary, secret-handling, path-traversal, or crypto regressions were introduced or amplified by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/test-implement-structure.sh:574-590
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Scanner omits implement-reachable shared vendor timing emitters, leaving A1/A2 incomplete despite the harness passing. With LARCH_TIMING_SKILL=design in the environment, implement lint-fix Codex rows via scripts/launch-codex-exec.sh:211 and Step 7a Claude code-flow rows via scripts/launch-claude-subprocess.sh:237 are recorded as design and ignored by implement timing reports. Pin DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement at the implement call sites or add an explicit launcher skill override, then extend the harness to cover those paths without mis-tagging review callers.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/launch-claude-ci.sh:192-199
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] A1 now pins LARCH_TIMING_SKILL on record-vendor-task but timing-ledger.sh rejects --vendor claude and the launcher swallows the failure. Claude CI-fix runs pass the new scanner yet still emit no vendor timing row, leaving implement timing reports incomplete under the false belief CI launchers are covered. Accept claude in timing-ledger record-vendor-task, or remove the call and document mark-only Claude CI telemetry.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: scripts/test-implement-structure.sh:605-607
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] A3 uses substring grep for workflow_path across 15 production emitter scripts. A harmless comment or doc string mentioning workflow_path in any scanned file breaks CI without a behavioral regression. Restrict checks to actual run-params reads or exclude comment-only matches.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/test-implement-structure.sh:617-618
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] A3 HARD/SIMPLE regex can match non-workflow prose in Step 2 dispatch files. Future comment or fixture text containing SIMPLE or HARD as standalone tokens fails the harness despite no workflow branching. Assert specific legacy workflow tokens/paths instead of bare tier words.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/record-implement-review-round-timing.sh:109-117
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] A1 scanner omits record-round emitters outside its 15-file enum and same-line pin rule. Step 5 deferred round timing can lose implement skill pinning without failing the new A1 guard. Add the helper to the scanner set and/or extend awk to record-round with export-or-same-line pin rules.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/record-implement-review-round-timing.sh:99-104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Round-only idempotency short-circuit predates this branch. Deferred Step 5 timing emit after a partial row exits 0 without updating start/end timestamps. Align pre-check with design helper full-tuple fingerprinting.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/launch-claude-ci.sh:192-199
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [latent] Claude CI vendor timing pin is applied to a record-vendor-task call that timing-ledger.sh rejects because only codex|cursor vendors are accepted. launch-claude-ci.sh invokes record-vendor-task --vendor claude, timing-ledger.sh returns 1, the launcher suppresses it with || true, and the new scanner still passes without any Claude CI timing row being recorded. Add claude as an accepted vendor with regression coverage for claude-ci-fix, or exclude launch-claude-ci.sh from the vendor-row contract if unsupported.
- **Suggested revision**: Address the concern above.

### FINDING_14: `2733f0a86` — Implement OOS housekeeping batch
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `2733f0a86` — Implement OOS housekeeping batch
- **Suggested revision**: Address the concern above.

### FINDING_15: `68d7ed4bc` — chore(larch-logs) flush (intentional run-log artifact; not reviewed as scope drift)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `68d7ed4bc` — chore(larch-logs) flush (intentional run-log artifact; not reviewed as scope drift) The implementation commit matches the plan: A1/A3 harness extensions, A2 timing-skill pins on five launchers, B monitor-level tests, C no-op (already fixed upstream), D1–D4 test/doc/comment updates. No production logic changes beyond telemetry env prefixes on existing `record-vendor-task` lines. ### Plan / acceptance traceability | Item | Status | |------|--------| | **A1** — awk scanner + retained literal greps | Present in `scripts/test-implement-structure.sh` | | **A2** — five launcher pins (`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement`) | Present; `launch-review.sh` untouched per plan | | **A3** — workflow-free Step 2 + `workflow_path` deny | Present | | **B** — `already_merged → Outcome.OK`, consecutive errors → `Outcome.TRANSIENT` | Two focused tests in `python/test_ci_monitor.py` | | **C** — verify-only | No diff (expected) | | **D1** — static Codex `.json` / `.cap-hit` exclusion fixtures | Present | | **D2/D3/D4** — comment/doc-only | Present across `larch-log.sh`, `SECURITY.md`, quiet-log docs | CI wiring is unchanged but sufficient: `test-implement-structure` and `test-larch-log-write-round` are already in `Makefile` harness buckets; `test_ci_monitor.py` is covered by `py-test`. ### Testing / regression assessment
- **Suggested revision**: Address the concern above.

### FINDING_16: **A1 scanner** correctly uses basename matching, same-line pin checks, and excludes comment-only `timing-ledger.sh` references (requires ` mark ` / `record-vendor-task`). Multi-line `record-vendor-task` continuations are safe because only the first line carries `timing-ledger.sh`.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **A1 scanner** correctly uses basename matching, same-line pin checks, and excludes comment-only `timing-ledger.sh` references (requires ` mark ` / `record-vendor-task`). Multi-line `record-vendor-task` continuations are safe because only the first line carries `timing-ledger.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_17: **A2** is statically enforced by the new scanner; runtime polluted-env attribution is not exercised, which aligns with the plan’s static-only acceptance.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **A2** is statically enforced by the new scanner; runtime polluted-env attribution is not exercised, which aligns with the plan’s static-only acceptance.
- **Suggested revision**: Address the concern above.

### FINDING_18: **B** tests fill a real gap: `test_poll_ci_three_consecutive_errors_bail` covers `poll_ci`; the new `test_monitor_*` cases cover `monitor()` outcome mapping (`Outcome.OK` for `already_merged`, `Outcome.TRANSIENT` with `"3 times consecutively"` detail). The `gh pr view` rc=1 stub path matches `gather_status` → three consecutive failures → transient classification via `retry.is_transient_net_signature`.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **B** tests fill a real gap: `test_poll_ci_three_consecutive_errors_bail` covers `poll_ci`; the new `test_monitor_*` cases cover `monitor()` outcome mapping (`Outcome.OK` for `already_merged`, `Outcome.TRANSIENT` with `"3 times consecutively"` detail). The `gh pr view` rc=1 stub path matches `gather_status` → three consecutive failures → transient classification via `retry.is_transient_net_signature`.
- **Suggested revision**: Address the concern above.

### FINDING_19: **D1** fixtures hit the existing deny clause at `scripts/larch-log.sh:74`; assertions mirror adjacent static-Codex exclusions.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **D1** fixtures hit the existing deny clause at `scripts/larch-log.sh:74`; assertions mirror adjacent static-Codex exclusions.
- **Suggested revision**: Address the concern above.

### FINDING_20: **Regression risk** is low: comment/doc edits, additive harness checks, env-prefix pins on timing calls, and two isolated unit tests.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **Regression risk** is low: comment/doc edits, additive harness checks, env-prefix pins on timing calls, and two isolated unit tests.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh` — Production `/implement` Step 5 path emits `timing-ledger.sh record-round` with `export LARCH_TIMING_SKILL=implement` on a separate line; the new A1 scanner (plan-scoped to `mark` / `record-vendor-task` / `timing-report.sh`) does not cover this subcommand. A dropped export would not fail the new harness.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `scripts/launch-review.sh` — `record-vendor-task` lines remain unpinned by design (serves `/review`). Intentional per plan; worth remembering when copying launcher patterns.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **risk-integration** `scripts/test-launch-claude-ci.sh` (and sibling CI launcher harnesses) — Plan’s optional A2 extension to assert `LARCH_TIMING_SKILL=implement` on CI launchers was not added; static coverage comes from `test-implement-structure.sh` only, not a runtime launcher smoke under polluted `LARCH_TIMING_SKILL=design`.
- **Suggested revision**: Address the concern above.

### FINDING_24: **risk-integration** `scripts/launch-claude-ci.sh:192-199` — This branch adds `launch-claude-ci.sh` to the A1 timing-pin scanner and applies an A2 `LARCH_TIMING_SKILL=implement` prefix on its `record-vendor-task` call, but `scripts/timing-ledger.sh:192` only accepts `--vendor codex|cursor`. The launcher passes `--vendor claude`, so `cmd_record_vendor_task` always returns 1 and the trailing `|| true` swallows the failure; no Claude CI-fix vendor rows are ever written. The new pin and scanner entry therefore imply guarded implement telemetry where none is recorded, which is a false-confidence integration risk rather than a real attribution fix. **Suggested fix:** Either teach `timing-ledger.sh` to accept `claude` when `task-kind` is `claude-ci-fix` (and add a harness asserting a row lands with `skill=implement`), or stop treating `launch-claude-ci.sh` as a vendor-row emitter in the A1 scanned set and document that Claude CI-fix wall time is not captured via `record-vendor-task`.
- **Reviewer**: dyn-telemetry-attribution-output.txt
- **Concern**: - **risk-integration** `scripts/launch-claude-ci.sh:192-199` — This branch adds `launch-claude-ci.sh` to the A1 timing-pin scanner and applies an A2 `LARCH_TIMING_SKILL=implement` prefix on its `record-vendor-task` call, but `scripts/timing-ledger.sh:192` only accepts `--vendor codex|cursor`. The launcher passes `--vendor claude`, so `cmd_record_vendor_task` always returns 1 and the trailing `|| true` swallows the failure; no Claude CI-fix vendor rows are ever written. The new pin and scanner entry therefore imply guarded implement telemetry where none is recorded, which is a false-confidence integration risk rather than a real attribution fix. **Suggested fix:** Either teach `timing-ledger.sh` to accept `claude` when `task-kind` is `claude-ci-fix` (and add a harness asserting a row lands with `skill=implement`), or stop treating `launch-claude-ci.sh` as a vendor-row emitter in the A1 scanned set and document that Claude CI-fix wall time is not captured via `record-vendor-task`.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-telemetry-attribution-output.txt
- **Concern**: - **risk-integration** `scripts/lint-fix-loop.sh:366-373` / `scripts/launch-codex-exec.sh:211-218` — `/implement` lint-fix still reaches an unpinned `record-vendor-task` through `lint-fix-loop.sh` → `launch-codex-exec.sh` (shared across design/review/research). Under a polluted `LARCH_TIMING_SKILL=design` shell, Codex lint-fix vendor rows can still be tagged `design` while the new 15-file scanner passes. This matches the plan’s intentional A2 exclusion of generic launchers; fixing it would need an implement-session guard at the lint-fix dispatch site, not a blanket `=implement` pin on `launch-codex-exec.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-telemetry-attribution-output.txt
- **Concern**: - **risk-integration** `scripts/test-implement-structure.sh:574-608` — The A1 guard is a fixed enumeration, not repo-wide discovery. New implement timing emitters added outside `implement_timing_emitters[]` (for example `skills/review-and-fix/scripts/record-implement-review-round-timing.sh`, which uses `export LARCH_TIMING_SKILL=implement` on the line before `record-round`) will not be caught unless the array is updated in the same change. The plan already calls this out as accepted maintenance surface.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-telemetry-attribution-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:107-110` — Implement Step 5 round timing uses `export LARCH_TIMING_SKILL=implement` on a separate line from `timing-ledger.sh record-round`, so the new same-line awk predicate would not apply even if this file were added to the scanner. Pre-existing; not worsened by the branch beyond the general fixed-list drift note above.
- **Suggested revision**: Address the concern above.

