### FINDING_10: [OUT_OF_SCOPE] Non-HARD runs now always invoke the driver and write `.step3.6-assessor.env` with `ASSESSOR_STATUS=skipped`; previously SIMPLE skipped without writing that file. That is an intentional contract extension and should not affect the WORSE gate (which requires `worse-majority` on HARD paths).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Non-HARD runs now always invoke the driver and write `.step3.6-assessor.env` with `ASSESSOR_STATUS=skipped`; previously SIMPLE skipped without writing that file. That is an intentional contract extension and should not affect the WORSE gate (which requires `worse-majority` on HARD paths).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_11: [OUT_OF_SCOPE] The harness mirrors handoff well but does not cover the plan’s “catch-all” abort when the driver exits `1` (only exit `2` and empty-key cases). Worth adding later; not a production-path bug given the driver never exits `1`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - The harness mirrors handoff well but does not cover the plan’s “catch-all” abort when the driver exits `1` (only exit `2` and empty-key cases). Worth adding later; not a production-path bug given the driver never exits `1`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] security: skills/design/scripts/assess-plan-round.sh:179
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Pre-existing LARCH_DISPATCH_PLAN_ASSESSORS_SH seam allows arbitrary dispatch script substitution. Same class as new driver seams; broader policy needed. Document and enforce a shared plugin-root allowlist for all LARCH_*_SH overrides repo-wide.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] risk-integration: skills/design/SKILL.md:1086-1088
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] WARN= replay from result env goes to chat without untrusted-data framing. Concurrent tmpdir tampering could inject operator-visible text; low likelihood in same-fence read. Optional untrusted wrapper for WARN replay or rely on atomic write + immediate read (current model).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] architecture: skills/design/scripts/design-plan-quality-assessor.sh:216-220
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] write-after rollback decrements review-round-count but write-cursor uses ROUND_NUM. Pre-existing inline semantics; count/cursor mismatch may confuse rollback debugging. Document pairing in assessor.md if not intentional.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:216-219` — Write-after rollback sets `review-round-count.txt` to `ROUND_NUM-1` but calls `write-cursor --value "$ROUND_NUM"`; this matches the pre-extraction inline lane (behavior-preserving), but it may leave cursor vs count inconsistent if that prior behavior was already wrong.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_35: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-plan-quality-assessor.sh:237-250` — `_assess_rc` is captured but never used; assess failures still settle via KV parse and `ASSESSOR_STATUS` defaults (same as the old inline path). Low risk while `assess-plan-round.sh` always exits `0` on settled paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_36: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **correctness** (verification) — `_assessor_parse_ok` is set on any allowlisted routing key in the file-read loop; stdout merge uses fill-only-unset (`-z "${!_assessor_key:-}"`); abort order (rc=2 → rc=0 empty status → catch-all) matches Step 2b postplan shape; non-HARD shows one orchestrator skip breadcrumb then invokes the driver (no duplicate skip line); `emit_kv` under default quiet mode goes to FD3, which is wired into `$()` capture in a child driver process—harness uses `LARCH_QUIET_DISABLE=1`, but production capture path is sound when quiet init runs in the driver subprocess. **Branch commits:** `dbb253d81` (extract driver), `0eff34913` (larch-logs), `11a04f421` (relevant-checks fixes).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] **Pre-existing rollback cursor write** — On `write-after` failure the driver still sets `review-round-count.txt` to `ROUND_NUM-1` but calls `write-cursor --value "$ROUND_NUM"` (not `ROUND_NUM-1`). That matches the removed inline `SKILL.md` block; this branch does not introduce it. If cursor and count are meant to stay aligned, that belongs to a separate change with `run-step3-review.sh` / cap semantics tests.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Pre-existing rollback cursor write** — On `write-after` failure the driver still sets `review-round-count.txt` to `ROUND_NUM-1` but calls `write-cursor --value "$ROUND_NUM"` (not `ROUND_NUM-1`). That matches the removed inline `SKILL.md` block; this branch does not introduce it. If cursor and count are meant to stay aligned, that belongs to a separate change with `run-step3-review.sh` / cap semantics tests.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] **`_assess_rc` is never consulted** — `design-plan-quality-assessor.sh` captures `assess-plan-round.sh` exit code but always settles at driver exit `0` after KV defaults. Safe today because `assess-plan-round.sh` only exits `0` or `2`, but a future non-zero “failure” exit without KVs would be treated as `ASSESSOR_STATUS=skipped` instead of triggering the orchestrator’s catch-all abort.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **`_assess_rc` is never consulted** — `design-plan-quality-assessor.sh` captures `assess-plan-round.sh` exit code but always settles at driver exit `0` after KV defaults. Safe today because `assess-plan-round.sh` only exits `0` or `2`, but a future non-zero “failure” exit without KVs would be treated as `ASSESSOR_STATUS=skipped` instead of triggering the orchestrator’s catch-all abort. --- ### Plan / requirements check | Requirement | Status | |-------------|--------| | Phase driver with `LARCH_*_SH` seams, pause checkpoint, `set +e` child calls | Met | | `.step3.6-assessor.env` via `phase_driver_write_result_env` + stdout KVs | Met | | `SKILL.md` qualified invoke, HARD `🔶` before invoke, postplan handoff + abort block | Met | | WORSE gate / Stop branch unchanged (prompt-side) | Met | | Harness + Makefile + `test-design-structure.sh` pins | Met | | Exit `0` settled / `2` config / never `1` | Met | --- ### Notes (non-findings)
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Quiet contract (`larch_quiet_init` + `emit_kv` on FD 3) matches `design-postplan-emit.sh`; command substitution in `SKILL.md` should still receive KVs the same way as the old inline `assess-plan-round.sh` capture.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Quiet contract (`larch_quiet_init` + `emit_kv` on FD 3) matches `design-postplan-emit.sh`; command substitution in `SKILL.md` should still receive KVs the same way as the old inline `assess-plan-round.sh` capture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

