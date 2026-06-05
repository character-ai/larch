### FINDING_1: code-quality: skills/design/scripts/record-plan-review-round-timing.sh:74-82
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Design deferred helper lacks ledger idempotency while implement deferred helper skips when a round row exists; MAV calls the helper directly from SKILL.md bypassing the in-process emit guard. A retried /design MAV adjudication step appends a second round-N ledger row; timing-report.json shows duplicate rounds[] objects for the same round. Add ledger-level idempotency (skill+step+round) to the design helper or route all design emissions through _emit_plan_round_timing_row.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:101-119
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] skills/review-and-fix/scripts/record-implement-review-round-timing.sh:51-95 Implement uses two parallel record-round paths with different count sources (IRF_LAST_* in-loop vs artifact greps in deferred helper). Future tally or MAV changes update artifacts but in-loop timing still uses stale IRF_LAST counts, or record-round flags diverge between paths. Consolidate through one wrapper with optional accepted/rejected overrides; keep artifact counting for deferred paths only.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/review-and-fix/scripts/record-implement-review-round-timing.sh:80-83
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Deferred idempotency matches only round number, not skill/step/interval. A bad prior row for the same round blocks a correct deferred re-emit after MAV without warning. Tighten the guard to skill+step+round (and optionally start_s) or replace only misattached rows.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: (plan) skills/design/scripts/test-plan-review-loop.sh skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan-listed tests for round-start-s snapshot survival and deferred emit before Step 7 mark are not present. MAV start pruning or commit-before-record regressions ship without mechanical detection. Add the two focused fixtures described in the implementation plan.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review-and-fix/scripts/record-implement-review-round-timing.md:9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract doc cites wrong harness files for the deferred implement helper. Maintainers look at generic timing tests and miss helper-specific coverage. Point the doc at test-record-implement-review-round-timing.sh.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/design/scripts/plan-review-loop.sh:1469-1486
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] panel-failed terminal path hand-rolls timing emit instead of using _snapshot_terminal_exit_preserving_status. A future terminal branch may omit timing emission while other statuses use the unified hook. Route panel-failed through the shared terminal snapshot+timing helper.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/timing-report.sh:381-388
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] emit_round_array uses bubble sort for round ordering. Fine at n<=5 but harder to extend if round caps increase. Use a simpler linearithmic awk sort if round volume grows.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/design/scripts/plan-review-loop.sh:1511-1527
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ACCEPTED_COUNT==0 block depends on _terminal_exit inside snapshot helper; fall-through would double-set status. Pre-existing control-flow fragility unrelated to this branch's primary timing changes. Refactor to explicit return/exit after terminal snapshot (separate cleanup).
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/design/scripts/record-plan-review-round-timing.sh:71-82
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Design deferred round helper lacks ledger idempotency that implement deferred helper has. MAV inline adjudication or a retry double-calls record-plan-review-round-timing.sh for the same round; timing-report.json gets duplicate round N objects with different durations. Add the same ledger row-exists guard used in record-implement-review-round-timing.sh (match skill, step label, and round number) before record-round.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-run-step5-review.sh:1-234
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Loop-mode Step 5 timing-only re-mark on --starting-round>1 is untested despite production code in run-step5-review.sh. Resume after MAV/commit could stop re-marking Step 5; later round rows attach to the first Step 5 interval and timing-report.json misreports per-round duration. Extend test-run-step5-review.sh with --mode loop --starting-round 2 and ledger assertions via timing-report.sh.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh:1-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required ordering test (deferred record-round before Step 7 mark) is missing. Deferred emit after commit-review-fixes would stretch round duration across Step 7 and break interval matching. Add a stub harness that logs mark vs record-round order around the deferred helper and a simulated commit path.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/review-and-fix/scripts/review-implement-step5-loop.sh:101-442
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No integration harness covers in-loop _emit_implement_round_timing_row across exit branches. A single missing _emit call on one stall/handoff branch drops per-round data for real /implement Step 5 runs. Add test-review-implement-step5-loop-timing.sh with stubbed round bodies for complete MAV-defer and one stall path.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/design/scripts/test-plan-review-loop.sh:1138-1154
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] panel-failed terminal path does not assert a design round timing row. _snapshot_terminal_exit_preserving_status regression for panel-failed could omit record-plan-review-round-timing.sh without CI failure. Call assert_plan_round_timing_row after the panel-failed scenario.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/design/scripts/test-plan-review-loop.sh:1550-1564
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] MAV deferral and round-start-s survival after snapshot are not timing-tested. MAV rounds could lose start timestamps or emit early rows with wrong counts. Assert no round row after MAV loop exit round-start-s present post-snapshot then optional deferred helper emit.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/SKILL.md:2137-2155
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Stall-path deferred implement timing is prose-only with no harness. Terminal stall after handoff checks/lint could skip record-implement-review-round-timing.sh and drop adjudication wall time. Add stub test for stall with round-start-s expecting one deferred ledger row without wrapper resume.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/scripts/test-record-plan-review-round-timing.sh:1-28
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Zero-count design round emission from the plan is not exercised. Empty review rounds might stop emitting rows and leave gaps in timing-report.json rounds arrays. Add fixture with zero findings and assert a round row with accepted=rejected=oos=0.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/design/scripts/test-record-plan-review-round-timing.md:1-3
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness doc overclaims negative-duration clamp coverage on the helper path. Contributors may assume helper clamp is tested when only timing-ledger.sh unit test covers it. Add inverted start/end helper case or update the md stub to point at test-timing-ledger.sh only.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Ledger isolation:** `design-publish.sh` and `render-final-summary.sh` bind `LARCH_TIMING_LEDGER` explicitly and `env -u IMPLEMENT_TMPDIR`, closing cross-skill ledger resolution bleed into published design timing JSON.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Ledger isolation:** `design-publish.sh` and `render-final-summary.sh` bind `LARCH_TIMING_LEDGER` explicitly and `env -u IMPLEMENT_TMPDIR`, closing cross-skill ledger resolution bleed into published design timing JSON.
- **Suggested revision**: Address the concern above.

### FINDING_19: **TSV / JSON safety:** `record-round` validates skill enum and uint fields, clamps durations, and `sanitize_field`s step labels; `emit_round_array` emits only numeric round fields (plus numeric `oos` for design).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **TSV / JSON safety:** `record-round` validates skill enum and uint fields, clamps durations, and `sanitize_field`s step labels; `emit_round_array` emits only numeric round fields (plus numeric `oos` for design).
- **Suggested revision**: Address the concern above.

### FINDING_20: **Path hygiene:** Deferred helpers reject symlink tmpdirs, canonicalize with `pwd -P`, and bind ledger to `$TMPDIR/timing-ledger.tsv` under validated roots via `timing-ledger.sh`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Path hygiene:** Deferred helpers reject symlink tmpdirs, canonicalize with `pwd -P`, and bind ledger to `$TMPDIR/timing-ledger.tsv` under validated roots via `timing-ledger.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_21: **Publish surface:** `design-log-publish.sh` excludes `timing-report-final.stderr.log` / `.failure.log`; `design-publish.sh` renders to a private `mktemp` dir, validates with `jq`, and atomically moves only JSON into `$DESIGN_TMPDIR`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Publish surface:** `design-log-publish.sh` excludes `timing-report-final.stderr.log` / `.failure.log`; `design-publish.sh` renders to a private `mktemp` dir, validates with `jq`, and atomically moves only JSON into `$DESIGN_TMPDIR`.
- **Suggested revision**: Address the concern above.

### FINDING_22: **Failure logging:** Render failures go through `append-tool-failure.sh --redact`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Failure logging:** Render failures go through `append-tool-failure.sh --redact`.
- **Suggested revision**: Address the concern above.

### FINDING_23: **Untrusted reviewer data:** Counting uses fixed `grep`/`awk` patterns on session artifacts; numeric outputs are re-validated before ledger write. SKILL.md handoff prose preserves the existing untrusted-data treatment for MAV ballots.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Untrusted reviewer data:** Counting uses fixed `grep`/`awk` patterns on session artifacts; numeric outputs are re-validated before ledger write. SKILL.md handoff prose preserves the existing untrusted-data treatment for MAV ballots. No command injection, path traversal, secret leakage, authz bypass, or unsafe deserialization was introduced. Committed `larch-logs/` timing enrichment is operational metadata (durations and finding counts), not a new secrets channel.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/review-and-fix/scripts/review-implement-step5-loop.sh:101-119
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] In-process timing guard is set before ledger append succeeds. flock timeout or append failure leaves STEP5_ROUND_N_TIMING_EMITTED=true with no round row; timing-report.json omits that round for the run. Set guard only after successful record-round; do not set guard when start_s/end_s validation fails before append.
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: skills/implement/SKILL.md:781-812
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Deferred implement round timing is prompt-orchestrator-only. Orchestrator omits record-implement-review-round-timing.sh after MAV/coder handoff; ledger lacks deferred wall time and counts despite successful review. Invoke deferred helper from run-step5-review.sh or a mandatory post-envelope shell hook when round-start-s exists.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: skills/review-and-fix/scripts/record-implement-review-round-timing.sh:80-83
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Idempotency keys only on round number column. Stray round row for same N blocks post-MAV deferred emit with correct counts. Scope idempotency check to skill+step (and optionally start_s).
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/timing-report.sh:381-406
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No deduplication of round rows in JSON emitter. Duplicate ledger rows yield duplicate round objects in timing-report.json. Keep last row per round number when building rounds array.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: skills/design/scripts/record-plan-review-round-timing.sh:71-82
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Design deferred helper lacks ledger idempotency. Second call path appends duplicate round rows. Add ledger duplicate check like implement helper.
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: skills/design/scripts/design-publish.sh:228-232
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Publish skips timing JSON when jq absent. Design run log publish ships without per-round timing-report batch content. Require jq for publish or degrade with explicit operator warning in run summary.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Helper harness omits plan-required deferred-before-Step-7 and stall-deferred-emit cases. Acceptance calls for those tests; without them a regression could record round duration after Step 7 marks and attach rounds to the wrong per_step interval in production JSON. Add fixtures to test-record-implement-review-round-timing.sh: assert record-round precedes Step 7 mark/commit stub; assert deferred emit on stall without resume wrapper.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: skills/design/scripts/test-plan-review-loop.sh:1550-1564
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] MAV deferral of timing emission is not regression-tested. Loop could start writing round rows before returning main-agent-vote-required, breaking deferred MAV wall-clock coverage without a failing test. After MAV loop run assert no design round row in timing-ledger.tsv and assert plan-review/round-N/round-start-s exists.
- **Suggested revision**: Address the concern above.

### FINDING_32: architecture: skills/review-and-fix/scripts/record-implement-review-round-timing.md:9
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness documentation does not match plan or Makefile targets. Contributors may think deferred handoff timing is fully tested when helper cases are still missing. Update md to reference test-record-implement-review-round-timing.sh and enumerate covered cases once implemented.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] correctness: skills/design/scripts/record-plan-review-round-timing.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Design deferred helper lacks ledger idempotency guard present on implement helper. A future duplicate call could append two round rows for the same round number and inflate analytics. Add the same round-number dedup awk guard used in record-implement-review-round-timing.sh.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] correctness: skills/design/scripts/plan-review-loop.sh:439-451
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] round-start-s snapshot survival is only covered by allowlist unit test. Allowlist drift or snapshot ordering changes could prune MAV start timestamps without CI catching it. Add plan-review-loop integration assert that round-start-s remains after _snapshot_terminal_exit_preserving_status on MAV path.
- **Suggested revision**: Address the concern above.

### FINDING_35: **correctness** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:81-83` — Deferred emission bails out when *any* ledger row has `$2 == "round"` and `$6 == N`, without checking that the row’s step label matches `"Step 5 — code review"` or that it would attach to the active Step 5 interval. A stray or mislabeled row for round *N* therefore blocks a later deferred MAV/coder emit from recording corrected `end_s` and post-MAV counts, while the bad row may still be dropped from `timing-report.json` by `emit_round_array`’s step/interval filter—yielding missing or stale per-round data. **Suggested fix:** Treat idempotency as satisfied only when a matching row exists for the same round number *and* step label (and optionally the same `start_s`), or delete/replace the prior row before appending the deferred row.
- **Reviewer**: dyn-telemetry-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:81-83` — Deferred emission bails out when *any* ledger row has `$2 == "round"` and `$6 == N`, without checking that the row’s step label matches `"Step 5 — code review"` or that it would attach to the active Step 5 interval. A stray or mislabeled row for round *N* therefore blocks a later deferred MAV/coder emit from recording corrected `end_s` and post-MAV counts, while the bad row may still be dropped from `timing-report.json` by `emit_round_array`’s step/interval filter—yielding missing or stale per-round data. **Suggested fix:** Treat idempotency as satisfied only when a matching row exists for the same round number *and* step label (and optionally the same `start_s`), or delete/replace the prior row before appending the deferred row.
- **Suggested revision**: Address the concern above.

### FINDING_36: **correctness** `skills/design/scripts/record-plan-review-round-timing.sh:71-82` — Unlike the implement deferred helper, the design helper always appends a new `round` row and has no ledger-level idempotency guard; only `plan-review-loop.sh`’s in-process `PLAN_ROUND_${n}_TIMING_EMITTED` guard prevents duplicates. `skills/design/SKILL.md` calls `record-plan-review-round-timing.sh` directly on the MAV path, so a duplicate orchestrator invocation would append two rows with the same round number. **Suggested fix:** Add the same “existing round row for this round# + step label” short-circuit used in `record-implement-review-round-timing.sh`, or route SKILL.md through a guarded wrapper shared with `plan-review-loop.sh`.
- **Reviewer**: dyn-telemetry-output.txt
- **Concern**: - **correctness** `skills/design/scripts/record-plan-review-round-timing.sh:71-82` — Unlike the implement deferred helper, the design helper always appends a new `round` row and has no ledger-level idempotency guard; only `plan-review-loop.sh`’s in-process `PLAN_ROUND_${n}_TIMING_EMITTED` guard prevents duplicates. `skills/design/SKILL.md` calls `record-plan-review-round-timing.sh` directly on the MAV path, so a duplicate orchestrator invocation would append two rows with the same round number. **Suggested fix:** Add the same “existing round row for this round# + step label” short-circuit used in `record-implement-review-round-timing.sh`, or route SKILL.md through a guarded wrapper shared with `plan-review-loop.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_37: **correctness** `scripts/timing-report.sh:381-406` — `emit_round_array` attaches every interval-matched ledger row and sorts by round number but does not dedupe on `round_num`; duplicate `round` rows (from the design gap above or any double-emit) produce multiple JSON objects with the same `"round": N` in one `per_step[].rounds` array, which breaks the acceptance expectation of one object per review round. **Suggested fix:** When building `match_idx`, keep only the last (or highest `end_s`) row per round number, or skip appending if that round number was already emitted for this step interval.
- **Reviewer**: dyn-telemetry-output.txt
- **Concern**: - **correctness** `scripts/timing-report.sh:381-406` — `emit_round_array` attaches every interval-matched ledger row and sorts by round number but does not dedupe on `round_num`; duplicate `round` rows (from the design gap above or any double-emit) produce multiple JSON objects with the same `"round": N` in one `per_step[].rounds` array, which breaks the acceptance expectation of one object per review round. **Suggested fix:** When building `match_idx`, keep only the last (or highest `end_s`) row per round number, or skip appending if that round number was already emitted for this step interval.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] The plan calls for harness cases such as “deferred row recorded before Step 7 parent mark” and “stall exit still emits deferred row”; `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh` covers counts/idempotency but not those ordering contracts—test gap, not proof the SKILL.md wiring is wrong.
- **Reviewer**: dyn-telemetry-output.txt
- **Concern**: - The plan calls for harness cases such as “deferred row recorded before Step 7 parent mark” and “stall exit still emits deferred row”; `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh` covers counts/idempotency but not those ordering contracts—test gap, not proof the SKILL.md wiring is wrong.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] Design runs that emit a timing mark labeled `design Step 3 — plan review (re-run)` (seen in historical logs) will not attach `round` rows recorded with the canonical `design Step 3 — plan review` step string; that label split predates this branch but still affects whether published `timing-report-final.json` shows `rounds` on the re-run `per_step` entry.
- **Reviewer**: dyn-telemetry-output.txt
- **Concern**: - Design runs that emit a timing mark labeled `design Step 3 — plan review (re-run)` (seen in historical logs) will not attach `round` rows recorded with the canonical `design Step 3 — plan review` step string; that label split predates this branch but still affects whether published `timing-report-final.json` shows `rounds` on the re-run `per_step` entry.
- **Suggested revision**: Address the concern above.

### FINDING_40: **risk-integration** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:342-347` — The `lint-fix-main-agent-required` path is a main-agent handoff like MAV/CMA, but it breaks the new deferral contract: the loop calls `_emit_implement_round_timing_row` and exits before orchestrator work, while `step5_persist_round_start` is only used for `main-agent-vote-required` / `coder-main-agent-required` (`237-249`). The Step 5 orchestrator only runs `record-implement-review-round-timing.sh` on stall when `round-$FINAL_ROUND_NUM/round-start-s` exists (`skills/implement/SKILL.md:781`), so this stall never gets a deferred row update. The ledger therefore records a round that ends at the lint handoff, excluding subsequent main-agent lint/fix wall time—the exact gap per-round timing was meant to close. **Suggested fix:** Treat `lint-fix-main-agent-required` like MAV/CMA: persist `round-start-s` at round entry, skip in-loop `_emit_implement_round_timing_row` on that branch, and let the orchestrator emit via `record-implement-review-round-timing.sh` after prompt-side lint work (success or terminal stall); add a harness case mirroring the MAV deferred/stall fixtures.
- **Reviewer**: dyn-handoff-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:342-347` — The `lint-fix-main-agent-required` path is a main-agent handoff like MAV/CMA, but it breaks the new deferral contract: the loop calls `_emit_implement_round_timing_row` and exits before orchestrator work, while `step5_persist_round_start` is only used for `main-agent-vote-required` / `coder-main-agent-required` (`237-249`). The Step 5 orchestrator only runs `record-implement-review-round-timing.sh` on stall when `round-$FINAL_ROUND_NUM/round-start-s` exists (`skills/implement/SKILL.md:781`), so this stall never gets a deferred row update. The ledger therefore records a round that ends at the lint handoff, excluding subsequent main-agent lint/fix wall time—the exact gap per-round timing was meant to close. **Suggested fix:** Treat `lint-fix-main-agent-required` like MAV/CMA: persist `round-start-s` at round entry, skip in-loop `_emit_implement_round_timing_row` on that branch, and let the orchestrator emit via `record-implement-review-round-timing.sh` after prompt-side lint work (success or terminal stall); add a harness case mirroring the MAV deferred/stall fixtures.
- **Suggested revision**: Address the concern above.

### FINDING_41: **risk-integration** `skills/design/scripts/record-plan-review-round-timing.sh:74-82` — The design deferred helper always appends a `round` ledger row, unlike `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:81-83`, which no-ops when a row for that round already exists. `skills/design/SKILL.md:1160` can invoke the design helper after MAV re-tally, and `plan-review-loop.sh` can emit via `_emit_plan_round_timing_row` → the same helper on terminal paths; a retry or orchestrator re-entry can therefore double-write the same round. `scripts/timing-report.sh:381-404` includes every interval-matched ledger row with no dedupe by round number, so duplicates surface as repeated `rounds[]` objects in `timing-report.json`. **Suggested fix:** Add the same ledger idempotency guard to `record-plan-review-round-timing.sh` (and optionally dedupe by round number in `emit_round_array` as defense-in-depth); extend `test-record-plan-review-round-timing.sh` with a second invocation asserting a single row.
- **Reviewer**: dyn-handoff-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/record-plan-review-round-timing.sh:74-82` — The design deferred helper always appends a `round` ledger row, unlike `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:81-83`, which no-ops when a row for that round already exists. `skills/design/SKILL.md:1160` can invoke the design helper after MAV re-tally, and `plan-review-loop.sh` can emit via `_emit_plan_round_timing_row` → the same helper on terminal paths; a retry or orchestrator re-entry can therefore double-write the same round. `scripts/timing-report.sh:381-404` includes every interval-matched ledger row with no dedupe by round number, so duplicates surface as repeated `rounds[]` objects in `timing-report.json`. **Suggested fix:** Add the same ledger idempotency guard to `record-plan-review-round-timing.sh` (and optionally dedupe by round number in `emit_round_array` as defense-in-depth); extend `test-record-plan-review-round-timing.sh` with a second invocation asserting a single row.
- **Suggested revision**: Address the concern above.

### FINDING_42: **risk-integration** `skills/implement/SKILL.md:814-816` — `mav-resume-past-cap` is handled as a clean completion (`follow the same post-Step-5 chain as complete`) with no call to `record-implement-review-round-timing.sh`, even though the resume entry path in `review-implement-step5-loop.sh:204-207` can return past-cap without executing another round body. If a MAV/CMA handoff left `round-$N/round-start-s` but deferred emit never ran (crash, skipped orchestrator step, or failed helper before ledger write), resuming with `--starting-round > EFFECTIVE_ROUND_CAP` drops that round from per-round telemetry entirely while still exiting success-shaped. **Suggested fix:** On `mav-resume-past-cap`, when `round-$FINAL_ROUND_NUM/round-start-s` exists and the ledger has no row for that round, invoke `record-implement-review-round-timing.sh` with a fresh `end_s` before continuing; cover with the deferred-helper “stall without resume wrapper” / past-cap fixtures enumerated in the plan.
- **Reviewer**: dyn-handoff-output.txt
- **Concern**: - **risk-integration** `skills/implement/SKILL.md:814-816` — `mav-resume-past-cap` is handled as a clean completion (`follow the same post-Step-5 chain as complete`) with no call to `record-implement-review-round-timing.sh`, even though the resume entry path in `review-implement-step5-loop.sh:204-207` can return past-cap without executing another round body. If a MAV/CMA handoff left `round-$N/round-start-s` but deferred emit never ran (crash, skipped orchestrator step, or failed helper before ledger write), resuming with `--starting-round > EFFECTIVE_ROUND_CAP` drops that round from per-round telemetry entirely while still exiting success-shaped. **Suggested fix:** On `mav-resume-past-cap`, when `round-$FINAL_ROUND_NUM/round-start-s` exists and the ledger has no row for that round, invoke `record-implement-review-round-timing.sh` with a fresh `end_s` before continuing; cover with the deferred-helper “stall without resume wrapper” / past-cap fixtures enumerated in the plan.
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] Plan-listed harness gaps remain: `test-record-implement-review-round-timing.sh` does not cover deferred-before-Step-7 ordering, `lint-fix-main-agent-required`, or stall-without-resume; `test-plan-review-loop.sh` asserts terminal round rows exist but not MAV defer-vs-double-emit or ledger idempotency.
- **Reviewer**: dyn-handoff-output.txt
- **Concern**: - Plan-listed harness gaps remain: `test-record-implement-review-round-timing.sh` does not cover deferred-before-Step-7 ordering, `lint-fix-main-agent-required`, or stall-without-resume; `test-plan-review-loop.sh` asserts terminal round rows exist but not MAV defer-vs-double-emit or ledger idempotency.
- **Suggested revision**: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] `review-implement-step5-loop.sh` one-shot guards (`STEP5_ROUND_${N}_TIMING_EMITTED`) are process-local only; cross-invocation safety for implement relies on the deferred helper’s ledger check, which is asymmetric with design as noted above.
- **Reviewer**: dyn-handoff-output.txt
- **Concern**: - `review-implement-step5-loop.sh` one-shot guards (`STEP5_ROUND_${N}_TIMING_EMITTED`) are process-local only; cross-invocation safety for implement relies on the deferred helper’s ledger check, which is asymmetric with design as noted above.
- **Suggested revision**: Address the concern above.

### FINDING_45: **risk-integration** `skills/design/scripts/render-final-summary.sh:216-217` — The new `_SKIP_TIMING_REGATHER` path skips assigning `tmrc`, but the duration-missing branch still evaluates `[ "$tmrc" -ne 0 ]` under `set -u`. After a successful pre-publish `timing-report-final.json`, if `DURATION` is empty (for example, JSON that passes `jq -e .` but lacks `total_hms` / `total_seconds`), `render-final-summary.sh` aborts with `tmrc: unbound variable` instead of finishing the post-publish summary. Because `design-publish.sh` invokes this helper with `|| true`, the failure is easy to miss while publish may already have completed. **Suggested fix:** When `_SKIP_TIMING_REGATHER=true`, set `tmrc=0` before the duration block, or gate the failure branch so `tmrc` is only read when regather ran; use `${tmrc:-0}` if you keep the combined test.
- **Reviewer**: dyn-publish-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/render-final-summary.sh:216-217` — The new `_SKIP_TIMING_REGATHER` path skips assigning `tmrc`, but the duration-missing branch still evaluates `[ "$tmrc" -ne 0 ]` under `set -u`. After a successful pre-publish `timing-report-final.json`, if `DURATION` is empty (for example, JSON that passes `jq -e .` but lacks `total_hms` / `total_seconds`), `render-final-summary.sh` aborts with `tmrc: unbound variable` instead of finishing the post-publish summary. Because `design-publish.sh` invokes this helper with `|| true`, the failure is easy to miss while publish may already have completed. **Suggested fix:** When `_SKIP_TIMING_REGATHER=true`, set `tmrc=0` before the duration block, or gate the failure branch so `tmrc` is only read when regather ran; use `${tmrc:-0}` if you keep the combined test.
- **Suggested revision**: Address the concern above.

### FINDING_46: **risk-integration** `skills/design/scripts/design-publish.sh:217-232` — `mktemp` failure and missing `jq` only call `add_warn` and delete `timing-report-final.*`; they do not append to `$DESIGN_TMPDIR/execution-issues.md`. The render-failure path at `245-254` does use `append-tool-failure.sh`, and the plan calls for warnings in `execution-issues.md` on failure. Committed run logs can therefore ship without any durable record that pre-publish timing render was skipped, even though `design-log-publish.sh` proceeds without `timing-report-final.json`. **Suggested fix:** Mirror the render-failure path: append a `Warnings` entry (or `append-execution-issue.sh`) for `mktemp` / missing-`jq` failures, not only `WARN_LINES` / result-env `WARN=` output.
- **Reviewer**: dyn-publish-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-publish.sh:217-232` — `mktemp` failure and missing `jq` only call `add_warn` and delete `timing-report-final.*`; they do not append to `$DESIGN_TMPDIR/execution-issues.md`. The render-failure path at `245-254` does use `append-tool-failure.sh`, and the plan calls for warnings in `execution-issues.md` on failure. Committed run logs can therefore ship without any durable record that pre-publish timing render was skipped, even though `design-log-publish.sh` proceeds without `timing-report-final.json`. **Suggested fix:** Mirror the render-failure path: append a `Warnings` entry (or `append-execution-issue.sh`) for `mktemp` / missing-`jq` failures, not only `WARN_LINES` / result-env `WARN=` output.
- **Suggested revision**: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] `scripts/design-log-publish.md` still documents the generic sidecar deny-list but does not mention the new explicit exclusions for `timing-report-final.stderr.log` and `timing-report-final.failure.log` added in `scripts/design-log-publish.sh:304`; operators reading only the doc may not know those sidecars are intentionally withheld from committed logs.
- **Reviewer**: dyn-publish-output.txt
- **Concern**: - `scripts/design-log-publish.md` still documents the generic sidecar deny-list but does not mention the new explicit exclusions for `timing-report-final.stderr.log` and `timing-report-final.failure.log` added in `scripts/design-log-publish.sh:304`; operators reading only the doc may not know those sidecars are intentionally withheld from committed logs.
- **Suggested revision**: Address the concern above.

### FINDING_48: **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:101-119` — `_emit_implement_round_timing_row` calls `timing-ledger.sh record-round` with only `LARCH_TIMING_SKILL=implement` and relies on inherited `LARCH_TIMING_LEDGER` / `IMPLEMENT_TMPDIR` resolution, while the new deferred helper in `record-implement-review-round-timing.sh` explicitly binds `LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"` and `design-publish.sh` pins the ledger and clears `IMPLEMENT_TMPDIR` before render. Because `resolve_ledger_path()` prefers a pre-set `LARCH_TIMING_LEDGER` over `IMPLEMENT_TMPDIR`, a stale or cross-run env value can land in-loop round rows in the wrong ledger (or skip writing) even though deferred handoff rows go to the correct file. **Suggested fix:** Mirror the deferred helper in `_emit_implement_round_timing_row` by exporting `LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"` (and `IMPLEMENT_TMPDIR` if needed) on every in-loop emit, matching the explicit tmpdir binding contract in the plan.
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:101-119` — `_emit_implement_round_timing_row` calls `timing-ledger.sh record-round` with only `LARCH_TIMING_SKILL=implement` and relies on inherited `LARCH_TIMING_LEDGER` / `IMPLEMENT_TMPDIR` resolution, while the new deferred helper in `record-implement-review-round-timing.sh` explicitly binds `LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"` and `design-publish.sh` pins the ledger and clears `IMPLEMENT_TMPDIR` before render. Because `resolve_ledger_path()` prefers a pre-set `LARCH_TIMING_LEDGER` over `IMPLEMENT_TMPDIR`, a stale or cross-run env value can land in-loop round rows in the wrong ledger (or skip writing) even though deferred handoff rows go to the correct file. **Suggested fix:** Mirror the deferred helper in `_emit_implement_round_timing_row` by exporting `LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"` (and `IMPLEMENT_TMPDIR` if needed) on every in-loop emit, matching the explicit tmpdir binding contract in the plan.
- **Suggested revision**: Address the concern above.

### FINDING_49: **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:92-98` and `skills/design/scripts/plan-review-loop.sh:414-420` — `step5_persist_round_start` and `_persist_plan_round_start` write `round-start-s` with no-clobber semantics but never validate that `start_s` is numeric before persisting, unlike `_emit_*` helpers which bail when `start_s`/`end_s` fail `^[0-9]+$`. A blank or corrupted value is persisted and later deferred emit fails validation in the helper (`exit 2`, swallowed by `|| true`), dropping MAV/handoff round timing silently. **Suggested fix:** Reuse the same uint guard before `printf` (skip persist and optionally warn when invalid), or read back and reject empty/non-numeric files before writing.
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:92-98` and `skills/design/scripts/plan-review-loop.sh:414-420` — `step5_persist_round_start` and `_persist_plan_round_start` write `round-start-s` with no-clobber semantics but never validate that `start_s` is numeric before persisting, unlike `_emit_*` helpers which bail when `start_s`/`end_s` fail `^[0-9]+$`. A blank or corrupted value is persisted and later deferred emit fails validation in the helper (`exit 2`, swallowed by `|| true`), dropping MAV/handoff round timing silently. **Suggested fix:** Reuse the same uint guard before `printf` (skip persist and optionally warn when invalid), or read back and reject empty/non-numeric files before writing.
- **Suggested revision**: Address the concern above.

### FINDING_50: **code-quality** `skills/implement/SKILL.md:796-801` — Round-1 feedback added deferred MAV/coder-main-agent timing to prose (“read `round-start-s`, invoke `record-implement-review-round-timing.sh`, then commit”), but the executable Bash fence that follows still jumps straight to `git add -A` and `commit-review-fixes.sh` with no fenced call to the new helper. `/implement` orchestrators are steered by Bash blocks; prose-only steps are easy to skip, so handoff rounds can reach Step 7 without a deferred `round` row despite the new instrumentation. **Suggested fix:** Add a Bash block before the commit fence that reads `round-start-s`, sets `end_s`, and invokes `record-implement-review-round-timing.sh` with `|| true`, matching the stall-branch instruction already added in the same section.
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `skills/implement/SKILL.md:796-801` — Round-1 feedback added deferred MAV/coder-main-agent timing to prose (“read `round-start-s`, invoke `record-implement-review-round-timing.sh`, then commit”), but the executable Bash fence that follows still jumps straight to `git add -A` and `commit-review-fixes.sh` with no fenced call to the new helper. `/implement` orchestrators are steered by Bash blocks; prose-only steps are easy to skip, so handoff rounds can reach Step 7 without a deferred `round` row despite the new instrumentation. **Suggested fix:** Add a Bash block before the commit fence that reads `round-start-s`, sets `end_s`, and invokes `record-implement-review-round-timing.sh` with `|| true`, matching the stall-branch instruction already added in the same section.
- **Suggested revision**: Address the concern above.

### FINDING_51: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `skills/design/scripts/record-plan-review-round-timing.sh` — Unlike `record-implement-review-round-timing.sh`, the design helper has no ledger-level idempotency check; only the in-process `PLAN_ROUND_${N}_TIMING_EMITTED` guard prevents duplicates. Low risk today because emission sites are single-process, but the asymmetry is worth aligning if deferred/design MAV paths grow.
- **Suggested revision**: Address the concern above.

### FINDING_52: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh` — The plan called for a fixture proving deferred `record-round` happens before any Step 7 timing mark from `commit-review-fixes.sh`; that ordering test is still absent (only count/idempotency cases are covered). Not a runtime bug by itself, but it leaves the highest-risk handoff invariant unenforced in CI.
- **Suggested revision**: Address the concern above.

### FINDING_53: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `scripts/timing-report.sh:381-407` — `emit_round_array` uses a global awk `match_idx[]` array (not declared in the function local list). Current call pattern does not appear to leak data into JSON output, but declaring `match_idx` local would match the plan’s “sequential arrays, never value subscripts” defensive style.
- **Suggested revision**: Address the concern above.

