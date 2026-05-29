### FINDING_15: [OUT_OF_SCOPE] **`skills/design/scripts/plan-review-loop.sh`** — Other inline Python heredocs (`plan_slot_human_label`, `plan_review_slot_for_reviewer`, findings dedup, etc.) still pose the same awk `^}$` truncation hazard if column-zero `}` appears in embedded Python; this PR only removes that risk from `_run_post_apply_pipeline`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **`skills/design/scripts/plan-review-loop.sh`** — Other inline Python heredocs (`plan_slot_human_label`, `plan_review_slot_for_reviewer`, findings dedup, etc.) still pose the same awk `^}$` truncation hazard if column-zero `}` appears in embedded Python; this PR only removes that risk from `_run_post_apply_pipeline`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/design/scripts/test-plan-review-loop.sh:1786-1920` — Eval-isolation tests still `eval "$(awk ... _run_post_apply_pipeline ...)"` to extract the function from `plan-review-loop.sh`. That trusts the repo copy of the shell file at test time; not introduced by this PR, but it remains a high-trust test pattern adjacent to the touched harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/design/scripts/dedup-plan-lines.py:445-484` — `open(..., errors="replace")` can silently substitute U+FFFD for invalid UTF-8 before `plan.txt` is re-emitted. Integrity/correctness concern for exotic byte sequences, not new command execution risk; same behavior as the removed heredoc.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] architecture: skills/design/scripts/plan-review-loop.sh:493-517,969-975
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Findings dedup fails open while plan-line dedup fails closed. A .plan-review-loop-dedup.py failure degrades the round and the loop can still reach cap-hit; a dedup-plan-lines.py failure terminates with emit-plan-failed. Operators may expect symmetric recovery. No change in this refactor; keep the intentional divergence documented (already improved in dedup-plan-lines.md and the new integration test).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/plan-review-loop.sh:1298-1299
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Terminal post-apply failures exit 0 from _terminal_exit. Scripts wrapping plan-review-loop.sh that only check $? after dedup-python-failed will treat the run as success despite LOOP_STATUS=emit-plan-failed. Document KV-driven status in plan-review reference, or revisit exit codes in a dedicated behavior change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/plan-review-loop.sh:518-555
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Backup is not restored after successful dedup if a later post-apply step fails. Validator or emit failure leaves a deduped plan.txt while the pre-revise backup is deleted, so the operator cannot roll back to the pre-dedup revise output. Only if full rollback is desired; would require extending failure paths beyond this refactor.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **code-quality** `skills/design/scripts/plan-review-loop.sh:207-993` — The loop still embeds several other Python heredocs (findings split, parse-collect-inline, `.plan-review-loop-dedup.py`, etc.). Only `_run_post_apply_pipeline` is awk-extracted in tests today; similar extraction could reduce future bash/Python coupling elsewhere. **Why out of scope:** pre-existing surface, not introduced or worsened by this diff (this PR reduces one heredoc).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

