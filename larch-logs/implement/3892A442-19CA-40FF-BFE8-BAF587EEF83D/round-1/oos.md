### FINDING_8: [OUT_OF_SCOPE] `cancelled-reentry-guard` missing from render-final-summary allowlist
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Pre-existing: `SKILL.md` emits `cancelled-reentry-guard` but `skills/design/scripts/render-final-summary.sh` (and related enums/docs) do not allow it. Re-entry guard runs the Final summary block, then the renderer rejects the unknown outcome and exits 2 instead of rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Historical CHANGELOG still documents `--simple` / `--hard` mutual exclusion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `CHANGELOG.md` still references `--simple`/`--hard` mutual exclusion in old release notes; operators may believe `--simple` remains valid. Excluded from plan completeness grep by design; update when touching changelog for a release.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

**Merge notes (for voters, not part of machine output):**
- Six plugin.json findings → **FINDING_1** (severity **important**; security’s **latent** subsumed).
- Structure tier-pin gaps (inputs 2, 3, 5, 9) → **FINDING_2** (severity **latent**; nit+latent sources).
- Testing **FINDING_8** (completeness harness) kept separate from **FINDING_2** (different fix: repo-wide `rg` + Makefile vs SKILL needles).
- Testing’s plugin.json CI-grep note stayed in **FINDING_3** concern, not duplicated under **FINDING_1**.
- Three `cancelled-reentry-guard` OOS items → **FINDING_8** with `[OUT_OF_SCOPE]` retained (**important** over **latent**).
- Inputs 6/12/20 were duplicates; input 13 stands alone as **FINDING_9**.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

