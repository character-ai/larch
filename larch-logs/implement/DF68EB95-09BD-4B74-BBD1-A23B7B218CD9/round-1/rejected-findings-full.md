### [rejected] FINDING_11

### FINDING_11: code-quality: skills/upgrade-larch/scripts/upgrade-larch.md:29
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Active-session prune doc still claims malformed session-env does not block pruning in a way that implied the old floor sweep. Reader expects unused olds can still be deleted under the 8-cap with malformed session metadata; after floor removal under-cap caches retain those dirs. Reword to tie old-version deletion to exceeding the retention cap and the newer-than-stable sanitize pass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: skills/upgrade-larch/scripts/test-upgrade-larch.sh (plan)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Diff does not show test-upgrade-larch.sh edits or proof the plan’s second harness ran. Cannot verify from diff alone that the broader upgrade harness still passes after the behavior change. Run test-upgrade-larch.sh in CI or before merge; add a change only if a failure appears.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.md (post-diff)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Limitations (Angle B) removed per plan; cross-train retention under cap no longer documented. Operators lose explicit note that non-current trains are not special-cased below the cap. Optional single-sentence retention note if product still wants that visibility.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

### FINDING_20: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.md:27-31
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Removing the former Limitations subsection drops the only explicit note that under the eight-version cap the cache is not aggressively minimized beyond removing versions newer than verified stable (and pins). An operator upgrades, sees several old patch directories still on disk with fewer than eight entries, and treats it as a failed prune or bug. Add a concise sentence under step 8 or a small Retention limits note describing under-cap behavior and what the cap loop does when count exceeds eight.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

### FINDING_8: code-quality: skills/upgrade-larch/scripts/test-upgrade-larch-prune.md:19-23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Edit-in-sync footer still names SKILL/Makefile/docs for any pruning change while this change set is narrower. Minor contributor confusion about whether follow-up doc edits are mandatory. Narrow the footer wording or confirm no consumer-facing drift in those files.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

