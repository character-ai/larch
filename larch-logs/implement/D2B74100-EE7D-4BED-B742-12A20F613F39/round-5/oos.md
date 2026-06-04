### FINDING_11: [OUT_OF_SCOPE] Plan wording vs postplan invalid-repo short-circuit before pause-save delegation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: PLAN_FINDING_2 describes delegating repo handling to `design-pause-save.sh` on internal pause, but invalid resolved repo fails inside postplan with `PAUSE_OK=false` and never execs pause-save. Debugging shows postplan invalid-repo output rather than pause-save invalid-repo. Behavior may match intent but diverges from plan delegation wording; document the short-circuit in `design-postplan-emit.md` or exec pause-save for one canonical invalid-repo path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] Intentional asymmetry: pause-save vs `design-publish` on contradictory publish stdout
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pause-save clears `RECOVERY_BRANCH` when normalizing contradictory `PUBLISH_OK=true` on non-zero exit while `design-publish` retains recovery metadata for failed-publish summaries. A publish that exits non-zero yet prints `PUBLISH_OK=true` and valid `RECOVERY_BRANCH` could show recovery hints in the summary but not get a resumable pause marker. Document the intentional asymmetry in `design-pause-save.md`, or preserve `RECOVERY_BRANCH` after sanitizing when stdout contradicted the exit code (overlaps in-scope FINDING_3 as a product/doc choice).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):**
- Original FINDING_1, 2, 13 → **FINDING_1** (same postplan invalid-`REPO` / Step 2b gap).
- Original FINDING_4, 11 → **FINDING_3** (same `RECOVERY_BRANCH` clearing on contradictory stdout); kept separate from **FINDING_12** (OOS plan/doc on that asymmetry).
- Original FINDING_9, 10 → **FINDING_8** (`validate_repo` duplication).
- Original FINDING_15 → **FINDING_11**; original FINDING_16 → **FINDING_12** (OOS retained in headings).
- No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

