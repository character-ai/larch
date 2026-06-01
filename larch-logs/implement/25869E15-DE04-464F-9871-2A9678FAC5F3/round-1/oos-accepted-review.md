### FINDING_10: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 4. **code-quality** `backfill_install_stamps` / `prune_cached_versions` toggle `nullglob` without save/restore. Pre-existing pattern in this file (`list_cached_versions_by_install_stamp`); not introduced by this diff. --- **Verdict:** Approve from a correctness lens. The three-layer fix (protect running dir, stamp all installs, backfill at prune) directly prevents the self-delete / redaction-unavailable failure mode and aligns with the plan.
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


