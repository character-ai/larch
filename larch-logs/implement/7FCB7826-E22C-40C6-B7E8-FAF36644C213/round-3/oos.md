### OOS_1: [OUT_OF_SCOPE] Branch mixes design-publish extraction with upgrade-larch and larch-logs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch mixes design-publish extraction with upgrade-larch #3320 and larch-logs commits (including CHANGELOG / SECURITY.md / installation docs churn). Reviewers may attribute unrelated SECURITY/upgrade behavior to Step 5c work or must separate #3133 scope from #3320 retention work. Increases diff noise for design-publish reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PR or document mixed scope in summary.
  - From cursor-specialist-edge-cases-output.txt: Split or note in PR description (process, not Step 5c logic).
  - From cursor-specialist-plan-fidelity-output.txt: Treat as distinct change set or split PR if policy requires single-feature diffs.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] upgrade-larch.sh changes belong under #3320 review, not design-publish acceptance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Upgrade-larch prune/backfill changes are substantial but unrelated to Step 5c plan; out of scope for design-publish acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Review under #3320 separately.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] phase_driver_read_result_env underused by SKILL orchestrators
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `lib-phase-driver.sh:59-83` — `phase_driver_read_result_env` is underused by SKILL orchestrators. Pre-existing maintainability gap amplified by the new 5c parse block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate when touching drivers again.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: [OUT_OF_SCOPE] upgrade-larch test gap pre-existing on branch baseline
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The upgrade path had no tests before this branch; same class as missing harness but pre-existing baseline rather than introduced solely by Step 5c extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address when touching upgrade-larch again.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] scripts/lib-net.sh executable bit churn
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Executable-bit change on `scripts/lib-net.sh` appears unrelated to design-publish; no Step 5c failure-path impact found.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Confirm intent or revert mode-only churn in a separate change.
  - From cursor-specialist-plan-fidelity-output.txt: Revert or ignore unless required by hook policy.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Success-path render-final-summary lacks || true asymmetry
- **Reviewer(s)**: dyn-shell-compat-output.txt
- **Severity**: nit
- **Concern**: Success-path `render-final-summary.sh` calls in `design-publish.sh:238-285` lack `|| true`, while the failed-plan-write path uses `|| true` (line 182). Today `render-final-summary.sh` always ends with `exit 0` after `render_or_fallback`, so this is unlikely to trip `set -e`; asymmetry remains if the render helper ever propagates non-zero statuses.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_7: [OUT_OF_SCOPE] Scout: upgrade-larch prune/backfill logic looks correct
- **Reviewer(s)**: dyn-prune-retention-output.txt
- **Severity**: nit
- **Concern**: Scout checks on `prune_cached_versions` (dual protected entries with `version_is_retained` dedup, `wc -w` cap at 8, `INSTALLED_VERSION` from `basename "$PLUGIN_ROOT"`) and `backfill_install_stamps` (empty/non-numeric stamp files do not skip backfill because `read_install_stamp` returns 1) look correct; no off-by-one or double-count defect found there.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] Scout: design-publish.sh matches plan; render unlikely to abort mid-tail
- **Reviewer(s)**: dyn-prune-retention-output.txt
- **Severity**: nit
- **Concern**: `design-publish.sh` matches the plan for ordering, `if ! plan-block-write.sh`, subshell capture on publish/upsert, rename guard (`SESSION_ID` non-empty and `PUBLISH_OK=true`), and exit-code contract; `render-final-summary.sh` uses internal `set +e` fallback and exits 0 on the success path, so the driver is unlikely to abort mid-tail on render alone.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Bash 3.2 portability and WARN-array patterns on branch diff
- **Reviewer(s)**: dyn-shell-compat-output.txt
- **Severity**: nit
- **Concern**: No `declare -A`, `mapfile`, `${var^^}`, or `&>>` in `design-publish.sh`; `parse_kv_from_output`’s `<<<"$text"` and `printf -v` in the SKILL block are Bash 3.2–safe; `${WARN_LINES[@]+"${WARN_LINES[@]}"}` is applied consistently in the driver’s `write_result_env_and_emit`. Orchestrator WARN dedup uses `"${_publish_warn_lines[@]}"` without `${array[@]+...}` guard, which is appropriate because the fenced block does not enable `set -u`. `backfill_install_stamps` correctly pairs `shopt -s nullglob` / `shopt -u nullglob` in upgrade-larch (pre-existing pattern).
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

