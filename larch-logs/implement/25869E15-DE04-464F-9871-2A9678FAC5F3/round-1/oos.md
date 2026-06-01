### FINDING_10: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 4. **code-quality** `backfill_install_stamps` / `prune_cached_versions` toggle `nullglob` without save/restore. Pre-existing pattern in this file (`list_cached_versions_by_install_stamp`); not introduced by this diff. --- **Verdict:** Approve from a correctness lens. The three-layer fix (protect running dir, stamp all installs, backfill at prune) directly prevents the self-delete / redaction-unavailable failure mode and aligns with the plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: risk-integration: docs/skills.md:147-153
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] edit-in-sync lists docs/skills.md but catalog was not updated for new prune stamp contract Minor doc drift between catalog and installation/security docs Add one sentence on stamp and prune behavior or narrow edit-in-sync list
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:1-422
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Script is not source-safe for unit tests Pre-existing barrier to cheap CI coverage; not introduced by this diff Consider BASH_SOURCE guard as follow-up if harnesses return
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] risk-integration: (repo)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No CI workflow exercises upgrade-larch behavior Pre-existing lint-only safety net for the skill None required for this PR unless team wants E2E upgrade tests
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] security: skills/upgrade-larch/scripts/upgrade-larch.sh:169-183
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] write_install_stamp uses LARCH_CACHE_DIR/$version without symlink guard Same symlink-follow write class as backfill; predates this branch Apply shared symlink-safe cache entry handling if hardening cache writes
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] security: skills/upgrade-larch/scripts/upgrade-larch.sh:284-297
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Prune deletion loop lacks /cleanup-style symlink skip on cache entries Pre-existing asymmetry with /cleanup trust model Consider ! -type l or -L skip on enumeration if cache symlink attacks are in threat model
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:199-201
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] list_cached_versions_by_install_stamp reads install stamp twice per stamped dir Slightly redundant I/O on large caches; not introduced by this branch Cache stamp in a local variable after first successful read
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] architecture: skills/upgrade-larch/scripts/upgrade-larch.sh:1-422
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Script not source-safe for offline prune tests Manual verification requires copying functions to a scratch script per plan No change in this PR per plan decision
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:251
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Prune log says most-recently-installed but retention may keep running version outside top-8 by stamp Operators may misread prune output after explicit running-version protection Update log wording on a follow-up if desired
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/upgrade-larch/scripts/upgrade-larch.sh:142-156` — `stat_mtime` returns `0` on failure; backfill correctly skips `mt=0`. Pre-existing helper; unchanged semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **architecture** Original issue scoped Defect C backfill out; the plan expanded scope and the code implements backfill. This is a requirements/plan divergence, not a logic error — behavior matches the plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **risk-integration** No committed offline harness for retention (plan Decision 1). Acceptance depends on manual verification; not a code defect.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

