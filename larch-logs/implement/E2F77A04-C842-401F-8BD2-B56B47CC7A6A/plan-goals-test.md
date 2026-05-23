## Goal
Fix aggregator degenerate-output handling: add 3-phase waterfall with substring-rejection guard so self-contradicting aggregator output is rejected rather than falsely synthesized as empty-merge attestation

## Implementation Plan
## Plan

Fix #2638 by wrapping the aggregator's dispatch + repair + validate sequence in `skills/review/scripts/aggregate-findings.sh` in a **narrow-trigger 3-phase waterfall** (Cursor → Codex → Claude). The trigger fires ONLY on a NEW validator rule: "zero `### FINDING_` blocks in output AND output text contains the literal substring `### FINDING_`". Pre-existing validation failures (`validation-failed` for missing attestation, impure attestation, unknown reviewer slot, etc.) continue to exit on first failure unchanged — no behavioral change for those paths, no regression risk for existing tests.

### Files modified

1. **`skills/review/scripts/aggregate-findings.sh`** — extract dispatch+repair+validate into `_attempt_aggregation_phase()` helper that returns phase status WITHOUT calling `append_warning`. Wrap in an outer phase loop. Build phase list from truthful `CURSOR_PRESENT`/`CODEX_PRESENT` (skip unavailable externals; Claude always appended as final). After each phase, inspect `ALL_OUTPUT_TOOLS` from the dispatcher — if internal Claude fallback fired during an outer Cursor/Codex phase, treat the outer phase as failed (so accounting stays truthful). Per-outer-phase output paths set explicitly via slot-manifest `output` field; consume `ALL_OUTPUT_FILES` to locate candidates (no `.phaseN` filename construction). Extend `emit_result()` to optionally emit `PHASES_ATTEMPTED=<comma-list>` (suppressed when only one phase ran) and the new `REASON=validation-exhausted` value. Add substring-rejection check in BOTH `_attempt_attestation_repair()` (before synthesis, emits `AGGREGATOR_SYNTHESIS_SUPPRESSED=preamble_finding_substring` breadcrumb) and validator `main()` (emits `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring` stderr line that the outer loop greps to decide on progression). Outer loop only calls `append_warning` once on terminal failure with a single consolidated entry.

2. **`skills/review/scripts/aggregate-findings.md`** — sibling contract: new waterfall behavior, new stdout keys (`PHASES_ATTEMPTED`, `REASON=validation-exhausted`), per-outer-phase output paths, synthesis-suppression breadcrumb.

3. **`skills/review/scripts/test-aggregate-findings.sh`** — new test cases:
   - `zero_findings_preamble_contradiction` (single-call, validator-focused): asserts phase 1 validator emits `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring` stderr; does not assert final REASON (waterfall is single-phase-capped via env or stub-success-on-phase2).
   - `waterfall_exhausted` (3-phase counter stub via heredoc-baked absolute counter path): asserts terminal `REASON=validation-exhausted`, `PHASES_ATTEMPTED=cursor,codex,claude`, all 3 outer-phase output files exist, findings.md unchanged, exactly ONE consolidated execution-issues.md entry.
   - `waterfall_recover_on_phase2`: phase 1 fails substring-rule, phase 2 succeeds → `REASON=ok`, `PHASES_ATTEMPTED=cursor,codex`, findings.md replaced, no execution-issues entry.
   - `waterfall_skip_unavailable_external`: `CODEX_PRESENT=false` → `PHASES_ATTEMPTED=cursor,claude`.
   - `empty_merge_negative_finding_prose`: documents the broad-rule behavior on backticked negative prose mentioning `### FINDING_`.
   - All existing tests (`zero_findings_no_attest`, `zero_findings_impure_attest`, `zero_findings_nonconforming_heading`, `zero_findings_nospace_pseudo_heading`, `zero_findings_prose_finding_ids`, `empty_merge_existing_token_passthrough`, `zero_findings_padded_attest`, `merge_plus_spurious_attest`) continue to pass unchanged.

4. **`skills/review/scripts/review-core.sh`** — after `aggregate-findings.sh` invocation, parse `REASON`. When `REASON=validation-exhausted`, byte-faithfully mirror the existing `panel-failed` short-circuit at lines 386-429: run `emit_tally_with_failure_isolation` with failure label `aggregator-validation-exhausted`, `flush_round_log`, `copy_to_parent`, emit the broader KV envelope (ACCEPTED_COUNT=0, REJECTED_COUNT=0, EXONERATED_COUNT=0, NEUTRAL_COUNT=0, OUT_OF_SCOPE_DRIFT_COUNT=0, FINDINGS_FILE, ACCEPTED_FINDINGS_FILE, REJECTED_FINDINGS_FILE, PANEL_MODE, PANEL_SHAPE), and `emit_kv REVIEW_CORE_STATUS aggregator-validation-exhausted` + `exit 2`. Voter dispatch is skipped.

5. **`skills/review/scripts/review-core.md`** — sibling contract: new `REVIEW_CORE_STATUS=aggregator-validation-exhausted` value, aggregator-exhaustion handoff, voter dispatch skipped on this path.

6. **`skills/review/scripts/test-review-core.sh`** — new regression test stubbing `aggregate-findings.sh` (via `REVIEW_CORE_AGGREGATE_FINDINGS_SH`) to emit `REASON=validation-exhausted`. Asserts `REVIEW_CORE_STATUS=aggregator-validation-exhausted` on stdout, voter dispatch NOT invoked, exit code 2, empty findings/accepted/rejected/oos files.

7. **`skills/review-and-fix/scripts/review-and-fix.sh`** — add `aggregator-validation-exhausted)` case to the `core_status` switch (line 1201, after `panel-failed`): `status="$core_status"`, `exit_code=2`, emit_breadcrumb. Status propagates to `IRF_LAST_ROUND_STATUS`.

8. **`skills/review-and-fix/scripts/review-implement-step5-loop.sh`** — add explicit `aggregator-validation-exhausted)` case to the `post_round_status` switch (line 131, after `panel-failed`): `step5_emit_final_envelope stall true aggregator-validation-exhausted ...`, `flush_review_batches`, `exit 2`.

9. **`skills/review-and-fix/scripts/test-review-and-fix.sh`** — new harness case stubbing `REVIEW_CORE_SH` to emit `REVIEW_CORE_STATUS=aggregator-validation-exhausted`. Asserts `IRF_LAST_ROUND_STATUS=aggregator-validation-exhausted`, exit code 2.

10. **`skills/implement/SKILL.md`** — Step 5 stall-reason table: add `aggregator-validation-exhausted` to the `Tool Failures` category enumeration (line ~1231).

11. **`SECURITY.md`** — refresh §"Pre-vote findings aggregation": document validation-driven 3-phase Cursor → Codex → Claude retry on structural-loss pattern, per-outer-phase artifacts retained in REVIEW_TMPDIR, terminal `validation-exhausted` stall behavior, substring-rejection guard in both validation and repair-synthesis paths.

### Approach summary

- **Locus**: retry logic stays inside `aggregate-findings.sh`. `dispatch-with-waterfall.sh` is unchanged.
- **Trigger discrimination**: outer loop progresses only on the specific substring-rejection signal (validator stderr token `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring`). Other validation failures continue legacy single-shot behavior.
- **Tool selection per outer phase**: presence flags scoped per call manipulate the dispatcher's internal phase choice, BUT outer loop inspects `ALL_OUTPUT_TOOLS` to catch any internal fallback and recount the phase accordingly.
- **Synthesis vs validation guard ordering**: substring check duplicated in `_attempt_attestation_repair` (suppresses incorrect synthesis recovery) and validator `main()` (signals outer-loop progression). Different roles, both required.
- **Observability**: `PHASES_ATTEMPTED` stdout KV + per-outer-phase output files (`aggregator-output.txt`, `aggregator-output-phase2-of-2.txt`, etc.) + single consolidated execution-issues.md entry on terminal exhaustion.

## Acceptance

1. **Substring guard rejects bug pattern**: Given aggregator output with zero `### FINDING_` blocks AND substring `### FINDING_` present in raw bytes (anywhere in output), `aggregate-validate.py` `main()` exits non-zero with stderr `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring`. `_attempt_attestation_repair()` also suppresses synthesis with stderr breadcrumb `AGGREGATOR_SYNTHESIS_SUPPRESSED=preamble_finding_substring`. `findings.md` is left unchanged.

2. **Waterfall progresses on substring-rejection only**: When phase 1 of the outer loop sees `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring`, the loop advances to phase 2 (Codex), then phase 3 (Claude) if phase 2 also fails. Other validation failures (`zero_findings_no_attest`, `zero_findings_impure_attest`, etc.) continue to exit on first failure as today. Existing test cases pass unchanged.

3. **Waterfall exhaustion surfaces as distinct stall**: When all 3 outer phases fail the substring check, `aggregate-findings.sh` emits `REASON=validation-exhausted` + `PHASES_ATTEMPTED=cursor,codex,claude`. `review-core.sh` short-circuits with the full panel-failed-shaped envelope and `REVIEW_CORE_STATUS=aggregator-validation-exhausted`, exit 2. `review-and-fix.sh` propagates `IRF_LAST_ROUND_STATUS=aggregator-validation-exhausted` with rc=2. `review-implement-step5-loop.sh` emits `STEP5_REVIEW_STATUS=stall`, `STALL_REASON=aggregator-validation-exhausted`. `/implement` Step 5 routes this to `Tool Failures` execution-issues.md category.

4. **No regression on existing aggregator paths**: `LARCH_AGGREGATOR_DISABLED=1` continues to pass-through with `REASON=disabled`. `INPUT_COUNT < 2` continues to pass-through with `REASON=insufficient-input`. All existing `test-aggregate-findings.sh` cases pass without modification. Existing stdout contract (AGGREGATED, INPUT_COUNT, MERGED_COUNT, REASON, FAILURE_LOG) unchanged on legacy paths; PHASES_ATTEMPTED is additive and suppressed on single-phase runs.

5. **Truthful tool-availability accounting**: When `CODEX_PRESENT=false`, the outer phase list is `(cursor claude)`. Outer-loop progresses cursor → claude (skipping codex). When the dispatcher's internal waterfall falls back to Claude inside an outer Cursor phase, `ALL_OUTPUT_TOOLS` reports `claude` and the outer loop treats the Cursor phase as failed, progressing to outer Codex (or Claude if Codex is also unavailable).

6. **Single consolidated execution-issues.md entry on exhaustion**: Recoverable phase failures (e.g., phase 1 fails, phase 2 succeeds) emit NO execution-issues entries. Only terminal exhaustion emits ONE entry with a consolidated warning naming all phases attempted.

7. **Regression test coverage**: `make test-aggregate-findings`, `make test-review-core`, and `make test-review-and-fix` all pass. `bash scripts/relevant-checks.sh` passes.

diff_lines: 400

## Test plan
(no test plan section in plan-file)
