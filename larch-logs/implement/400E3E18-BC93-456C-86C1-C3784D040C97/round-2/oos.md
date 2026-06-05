### FINDING_33: [OUT_OF_SCOPE] correctness: skills/design/scripts/record-plan-review-round-timing.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Design deferred helper lacks ledger idempotency guard present on implement helper. A future duplicate call could append two round rows for the same round number and inflate analytics. Add the same round-number dedup awk guard used in record-implement-review-round-timing.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] correctness: skills/design/scripts/plan-review-loop.sh:439-451
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] round-start-s snapshot survival is only covered by allowlist unit test. Allowlist drift or snapshot ordering changes could prune MAV start timestamps without CI catching it. Add plan-review-loop integration assert that round-start-s remains after _snapshot_terminal_exit_preserving_status on MAV path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_38: [OUT_OF_SCOPE] The plan calls for harness cases such as “deferred row recorded before Step 7 parent mark” and “stall exit still emits deferred row”; `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh` covers counts/idempotency but not those ordering contracts—test gap, not proof the SKILL.md wiring is wrong.
- **Reviewer**: dyn-telemetry-output.txt
- **Concern**: - The plan calls for harness cases such as “deferred row recorded before Step 7 parent mark” and “stall exit still emits deferred row”; `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh` covers counts/idempotency but not those ordering contracts—test gap, not proof the SKILL.md wiring is wrong.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_39: [OUT_OF_SCOPE] Design runs that emit a timing mark labeled `design Step 3 — plan review (re-run)` (seen in historical logs) will not attach `round` rows recorded with the canonical `design Step 3 — plan review` step string; that label split predates this branch but still affects whether published `timing-report-final.json` shows `rounds` on the re-run `per_step` entry.
- **Reviewer**: dyn-telemetry-output.txt
- **Concern**: - Design runs that emit a timing mark labeled `design Step 3 — plan review (re-run)` (seen in historical logs) will not attach `round` rows recorded with the canonical `design Step 3 — plan review` step string; that label split predates this branch but still affects whether published `timing-report-final.json` shows `rounds` on the re-run `per_step` entry.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_43: [OUT_OF_SCOPE] Plan-listed harness gaps remain: `test-record-implement-review-round-timing.sh` does not cover deferred-before-Step-7 ordering, `lint-fix-main-agent-required`, or stall-without-resume; `test-plan-review-loop.sh` asserts terminal round rows exist but not MAV defer-vs-double-emit or ledger idempotency.
- **Reviewer**: dyn-handoff-output.txt
- **Concern**: - Plan-listed harness gaps remain: `test-record-implement-review-round-timing.sh` does not cover deferred-before-Step-7 ordering, `lint-fix-main-agent-required`, or stall-without-resume; `test-plan-review-loop.sh` asserts terminal round rows exist but not MAV defer-vs-double-emit or ledger idempotency.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_44: [OUT_OF_SCOPE] `review-implement-step5-loop.sh` one-shot guards (`STEP5_ROUND_${N}_TIMING_EMITTED`) are process-local only; cross-invocation safety for implement relies on the deferred helper’s ledger check, which is asymmetric with design as noted above.
- **Reviewer**: dyn-handoff-output.txt
- **Concern**: - `review-implement-step5-loop.sh` one-shot guards (`STEP5_ROUND_${N}_TIMING_EMITTED`) are process-local only; cross-invocation safety for implement relies on the deferred helper’s ledger check, which is asymmetric with design as noted above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_47: [OUT_OF_SCOPE] `scripts/design-log-publish.md` still documents the generic sidecar deny-list but does not mention the new explicit exclusions for `timing-report-final.stderr.log` and `timing-report-final.failure.log` added in `scripts/design-log-publish.sh:304`; operators reading only the doc may not know those sidecars are intentionally withheld from committed logs.
- **Reviewer**: dyn-publish-output.txt
- **Concern**: - `scripts/design-log-publish.md` still documents the generic sidecar deny-list but does not mention the new explicit exclusions for `timing-report-final.stderr.log` and `timing-report-final.failure.log` added in `scripts/design-log-publish.sh:304`; operators reading only the doc may not know those sidecars are intentionally withheld from committed logs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_51: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `skills/design/scripts/record-plan-review-round-timing.sh` — Unlike `record-implement-review-round-timing.sh`, the design helper has no ledger-level idempotency check; only the in-process `PLAN_ROUND_${N}_TIMING_EMITTED` guard prevents duplicates. Low risk today because emission sites are single-process, but the asymmetry is worth aligning if deferred/design MAV paths grow.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_52: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh` — The plan called for a fixture proving deferred `record-round` happens before any Step 7 timing mark from `commit-review-fixes.sh`; that ordering test is still absent (only count/idempotency cases are covered). Not a runtime bug by itself, but it leaves the highest-risk handoff invariant unenforced in CI.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_53: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `scripts/timing-report.sh:381-407` — `emit_round_array` uses a global awk `match_idx[]` array (not declared in the function local list). Current call pattern does not appear to leak data into JSON output, but declaring `match_idx` local would match the plan’s “sequential arrays, never value subscripts” defensive style.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/design/scripts/plan-review-loop.sh:1511-1527
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ACCEPTED_COUNT==0 block depends on _terminal_exit inside snapshot helper; fall-through would double-set status. Pre-existing control-flow fragility unrelated to this branch's primary timing changes. Refactor to explicit return/exit after terminal snapshot (separate cleanup).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

