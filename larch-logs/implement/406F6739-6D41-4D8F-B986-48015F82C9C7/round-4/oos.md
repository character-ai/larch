### FINDING_10: [OUT_OF_SCOPE] risk-integration: scripts/test-design-structure.sh:931
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness pins approval-gates to old inner-env-only MainAgent wording Blocks fixing approval-gates drift without harness change Update pin when approval-gates.md is aligned
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/design/references/plan-review.md:48
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Caller prose still names SKILL.md Step 3 directly instead of run-step3-review.sh. Doc drift only; not introduced by this diff’s stated doc-sync scope. Update when doing a broader design doc pass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/design/scripts/run-step3-review.sh:154-191` — `RUN_STEP3_PLAN_REVIEW_LOOP_SH` and `RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH` allow overriding which executables run, without constraining paths to `PLUGIN_ROOT`. This matches the existing Step 2 dispatcher test-injection pattern and sits inside larch’s same-UID trust model; a same-UID writer who could poison these env vars could already tamper with session artifacts or skill prompts. **Why out of scope:** convention is pre-established elsewhere; residual risk is unchanged in kind, only the Step 3 surface is new.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/design/scripts/run-step3-review.sh:104-115,146-147` — Writes to `.step3-review-cap.env` and `review-round-count.txt` do not refuse symlink targets (unlike `.step3-review-result.env`). **Why out of scope:** behavior is ported from pre-refactor inline Step 3; impact is reduced because the orchestrator no longer `source`s the cap env file. --- **Verdict:** From a security/trust-boundary lens, this branch is sound. Symlink guards, allowlisted KV parsing, and removal of `source` on session artifacts are the right direction; no new exploitable cross-boundary paths were identified under larch’s documented same-UID model.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] correctness: skills/design/scripts/run-step3-review.sh:121-137
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Cap-reached path still deletes plan-review/round-* artifacts before skipping loop. Pre-existing; cap hit on 3rd/5th review run wipes round forensics operators might expect to keep. Consider skipping cleanup when STEP3_REVIEW_CAP_REACHED=true (future change).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_34: [OUT_OF_SCOPE] **Persist/rollback** — `run-step3-review.sh:254-264` matches the removed SKILL logic (`tally-error` via `TALLY_PLAN_REVIEW_STATUS` or `LOOP_STATUS`, plus `degraded-empty-collector`; rollback to `_step3_prior_round_count`; otherwise keep `STEP3_REVIEW_ROUND_NUM`). The driver also updates `REVIEW_ROUND_COUNT` on rollback (new breadcrumb only).
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **Persist/rollback** — `run-step3-review.sh:254-264` matches the removed SKILL logic (`tally-error` via `TALLY_PLAN_REVIEW_STATUS` or `LOOP_STATUS`, plus `degraded-empty-collector`; rollback to `_step3_prior_round_count`; otherwise keep `STEP3_REVIEW_ROUND_NUM`). The driver also updates `REVIEW_ROUND_COUNT` on rollback (new breadcrumb only).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] **LOOP_STATUS normalization** — The allow-list regex at `run-step3-review.sh:247-250` is the same as the removed fence; `skills/design/SKILL.md:881-884` still supplies a second `panel-failed` fallback only when `LOOP_STATUS` is empty after sourcing / stdout parse. Symlink-inner-env and stdout-only paths are handled inside the driver before writing `.step3-review-result.env`.
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **LOOP_STATUS normalization** — The allow-list regex at `run-step3-review.sh:247-250` is the same as the removed fence; `skills/design/SKILL.md:881-884` still supplies a second `panel-failed` fallback only when `LOOP_STATUS` is empty after sourcing / stdout parse. Symlink-inner-env and stdout-only paths are handled inside the driver before writing `.step3-review-result.env`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] **HARD write-cursor failure** — Behavior intentionally diverges from the old bare `exit 1` (`diff.txt` ~655): the driver now writes `LOOP_STATUS=panel-failed`, leaves the pending round persisted, and exits `1` (`run-step3-review.sh:164-185`), with harness coverage in `test-run-step3-review.sh`. SKILL recovers via stdout when rc≠0 blocks sourcing (`856-877`).
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **HARD write-cursor failure** — Behavior intentionally diverges from the old bare `exit 1` (`diff.txt` ~655): the driver now writes `LOOP_STATUS=panel-failed`, leaves the pending round persisted, and exits `1` (`run-step3-review.sh:164-185`), with harness coverage in `test-run-step3-review.sh`. SKILL recovers via stdout when rc≠0 blocks sourcing (`856-877`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

### FINDING_37: [OUT_OF_SCOPE] **CODEX_PRESENT default** — Driver passes `"${CODEX_PRESENT:-false}"` (`202-203`) vs the old `"$CODEX_PRESENT"`; if session env ever leaves these unset, the old path failed closed in `plan-review-loop.sh` argv validation (exit `2`), while the new path defaults to `false`. Likely benign if Step 0 always sets the flags.
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **CODEX_PRESENT default** — Driver passes `"${CODEX_PRESENT:-false}"` (`202-203`) vs the old `"$CODEX_PRESENT"`; if session env ever leaves these unset, the old path failed closed in `plan-review-loop.sh` argv validation (exit `2`), while the new path defaults to `false`. Likely benign if Step 0 always sets the flags.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_40: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-allowlist-variable-injection-output.txt
- **Concern**: - **security** `skills/design/scripts/plan-review-loop.sh:154-173` — `write_step3_result_env` writes inner result keys with raw `printf '%s\n'` and no newline guard, while stdout uses `emit_kv` which rejects multiline values (`scripts/lib-quiet.sh:166-172`). This pre-existing gap is the practical write path for multiline inner-env content; the branch amplifies its impact only because `run-step3-review.sh:221-224` lost the per-line `case` guard that main/`SKILL.md` previously applied.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_41: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-allowlist-variable-injection-output.txt
- **Concern**: - **security** `skills/design/SKILL.md:860-876` — The new orchestrator fence correctly uses a `case` allowlist before each `printf -v` when sourcing `.step3-review-result.env` and stdout fallback; allowlisted keys are intentional orchestrator state (`LOOP_STATUS`, `REVIEW_ROUND_COUNT`, etc.) and exclude bash specials. Residual multiline spill could still set a second allowlisted key (e.g. forged `REVIEW_ROUND_COUNT`) if a tampered result env contained embedded newlines, but driver-written values are regex/numeric constrained, so this is lower risk than the inner-env path above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/run-step2-dispatch.sh:15-23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] session_get duplicates new phase_driver_session_get Pre-existing duplication not introduced by this branch; lib foundation not yet adopted by implement stack Refactor run-step2-dispatch to source lib-phase-driver.sh when next implement driver lands
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_6: risk-integration: skills/design/references/approval-gates.md:90-100
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Gate B still normatively reads .step3-plan-review-result.env while Step 3 handoff uses .step3-review-result.env On cap-reached re-entry stale inner env can say converged while driver wrote cap-reached only to normalized env; agent following approval-gates may enter passive-summary/Gate B incorrectly Update approval-gates.md and test-design-structure.sh pin 931 to prefer .step3-review-result.env for LOOP_STATUS; keep inner env loop-internal
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] correctness: skills/design/SKILL.md:826
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Cap prose omits degraded-empty-collector rollback mention Misleading doc only; driver and branch matrix handle degraded path Add degraded-empty-collector to cap-guard prose for parity with driver
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

