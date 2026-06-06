### OOS_1: [OUT_OF_SCOPE] Step 2a.5 SIMPLE repair fence pause-before-write ordering predates Phase 7
- **Reviewer(s)**: dyn-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: The Step 2a.5 SIMPLE repair fence runs `design-pause-save.sh` at line 844 before conditional `step-2a` / `step-2a.5` writes at lines 869–874. That ordering predates Phase 7 (unchanged in the diff) and violates the new before-pause contract on legacy SIMPLE repair resumes; it is not covered by `assert_folded_sentinel_writes`.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] step-5c harness lacks positive in-fence ordering assertion
- **Reviewer(s)**: dyn-sentinel-ordering-output.txt
- **Severity**: latent
- **Concern**: `assert_folded_sentinel_writes` negative-checks an unconditional `step-5c` inside the publish fence and greps prose for the gated write, but does not positive-assert in-fence ordering or the `PLAN_WRITE_OK` parse/decision guard the plan specified. This aligns with the `step-5c` prose deferral and weakens regression detection for that failure mode.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Plan assessor artifacts outside deny patterns
- **Reviewer(s)**: dyn-deny-list-gaps-output.txt
- **Severity**: latent
- **Concern**: Assessor artifacts (`claude-plan-assessor-round-*.txt`, `codex-plan-assessor-round-*.txt`, `cursor-plan-assessor-round-*.txt` and their `.diag`/`.json` sidecars from `assess-plan-round.sh`) are outside the new deny patterns because they lack `-output` in the basename. No committed top-level assessor files were found, so exposure may be limited by lifecycle cleanup rather than explicit denial.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Deny-list maintained manually in parallel with case arms
- **Reviewer(s)**: dyn-deny-list-gaps-output.txt
- **Severity**: latent
- **Concern**: The ~40-entry denied-basename list in `test-design-log-publish.sh` is maintained manually in parallel with `design_artifact_excluded()` case arms; there is no table-driven call into the function itself. That predates this branch but remains the main regression path if a new producer basename is added without updating both sites.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

