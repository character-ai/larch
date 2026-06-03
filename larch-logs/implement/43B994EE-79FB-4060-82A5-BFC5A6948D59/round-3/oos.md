### OOS_1: [OUT_OF_SCOPE] Duplicated `semver_lt` across bump scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-existing `semver_lt` in `apply-bump.sh` (lines 42–52) duplicates `release-set-version` pattern; repo-wide semver comparison may drift across bump paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate semver helpers in a follow-up.

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Legacy `promote-latest-release.sh` vs new `/release` flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Legacy promote-newest script coexists with new cut-a-release flow; two promotion models in one skill directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Deprecate or clearly fence legacy script in docs only.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] `apply-bump.sh` origin race retry not mirrored on release path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `apply-bump.sh` retries on `origin/main` same-version race; release PR path has no analogous retry if concurrent merges land during CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Out of scope; optional follow-up retry in create-pr/ci-wait

---


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] No offline harness for `--base` + `--head origin/main` together
- **Reviewer(s)**: dyn-classify-bump-head-coordination-output.txt
- **Severity**: nit
- **Concern**: `test-classify-bump.sh` Test 6 uses `--base` only; `test-release-prepare.sh` fakes `git` but uses host `git diff`—head/base coordination regressions may only surface in live operator runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct fix bullet beyond the concern; overlaps FINDING_10 in-scope test gap.)

---

**Subsumed without separate blocks** (same risk already covered, or explicit “no defect” attestation): input FINDING_31, 32, 37, 38 (no in-scope action); FINDING_33 folded into FINDING_2 plan-fidelity strand; duplicate `release-finish` polls merged into FINDING_2; FINDING_23 merged into FINDING_8.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

