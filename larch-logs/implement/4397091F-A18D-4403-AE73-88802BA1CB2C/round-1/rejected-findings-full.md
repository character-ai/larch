### [rejected] FINDING_11

### FINDING_11: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:1032-1039
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test pass strings say review-scout-manifest.json committed but only file existence under tmp log root is checked. Misleading signal when triaging test failures vs real git commits. Reword assertions to written or present at log root.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_15

### FINDING_15: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1098-1100
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] SCOUT_STATUS check is case-sensitive for na only. Emitters using NA would trigger a scout manifest flush contrary to na semantics. Normalize SCOUT_STATUS before comparison or document case-sensitive contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1098-1101
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] SCOUT_STATUS guard is only != na after :-na default; does not trim. Malformed SCOUT_STATUS value that is only whitespace still flushes a misleading status string. Trim/normalize empty-after-trim to na or add explicit -n check on the final value.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1115-1120
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Replace-mode review-scout-manifest at run root overwrites prior rounds. Multi-round run: only latest round summary in flat batch; earlier round summaries lost at run root (round-N dirs may still hold per-round scout files). Document latest-only semantics or add round-scoped batch if flat history is required.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_5

### FINDING_5: architecture: skills/review-and-fix/scripts/review-and-fix.sh:1094-1167; skills/review/SKILL.md:57-86
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Implement-path review-scout-manifest flush runs before flush_review_batches (tally / review-findings-full), whereas SKILL.md specifies scout manifest after the tally batch for /review. A consumer that assumes identical inter-batch ordering between standalone /review logs and /implement Step 5 logs could mis-order or mis-interpret batched events. If parity is required, relocate the flush to after tally (or document intentional ordering difference).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_6

### FINDING_6: code-quality: scripts/test-larch-log.sh:219-245; skills/review-and-fix/scripts/test-review-and-fix.sh:1032-1073
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test pass strings say committed while only filesystem placement under tmp log root is asserted. Operators misread failures as git staging/commit problems. Use wording like written or present under larch-logs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc says non-empty and not na; code does not mention whitespace-only SCOUT_STATUS. Readers assume stronger validation than implemented. Align documentation with guard or tighten guard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc claims non-empty and not na; implementation maps empty to na. Readers may expect different gating than the shell default. Update prose to match scout_status_val=${scout_status_val:-na} and != na.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

