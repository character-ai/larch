### OOS_1: [OUT_OF_SCOPE] Pre-existing semver_lt duplication in ship-pr.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh:845+` duplicates semver compare logic; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate in a follow-up


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] promote-release.sh lacks unique isLatest guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-release-idempotency-output.txt
- **Severity**: latent
- **Concern**: `scripts/promote-release.sh` (~79) does not fail closed when multiple `isLatest=true` releases exist; ambiguous `CURRENT_LATEST` string compare if GitHub metadata is corrupt. `/release` depends on promote more heavily but ambiguity predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add fail-closed Latest count in promote-release.sh later
  - From cursor-specialist-correctness-output.txt: Use jq -r '.[0]' or fail on count != 1.
  - From cursor-specialist-edge-cases-output.txt: Count isLatest rows and exit 1 if count != 1.
  - From dyn-release-idempotency-output.txt: (same concern as above; no additional distinct proposal beyond count enforcement)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Pre-existing classify-bump leading-zero math
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `classify-bump.sh:316-320` uses `$((MAJ + 1))` without `10#`; same leading-zero/octal class if versions ever carry leading zeros; not introduced by this branch’s diff hunk.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No slot provided a distinct fix beyond noting pre-existing scope; dyn-shell-portability listed it as follow-up class only.)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: [OUT_OF_SCOPE] No automated test for release-tag.yaml vs release-finish race
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `.github/workflows/release-tag.yaml` ordering/race with orchestrator finish is manual-only; pre-existing gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Future workflow fixture or fork smoke (pre-existing gap).


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] create-pr.sh redaction supporting change
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/create-pr.sh:2424-2434` now redacts secrets in PR bodies; not in plan file list but supports release notes safety. No action required for Phase 3 unless scope control matters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: N/A (supporting change). No action required for Phase 3 unless scope control matters.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] test-promote-release.sh does not assert gh --repo threading
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-promote-release.sh:2757-2787` promote-release `--repo` harness does not assert `gh` argv threading; regression could drop `--repo` on one call without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Extend fake gh to require --repo when fixture expects it.

---

**Merge notes (for voters):** Raw inputs 50–52 and 56–59 were positive traces or non-actionable attestations and were omitted. Inputs 1/10/16/42/53 → FINDING_1; 2/11/43 → FINDING_2; 18/48 → FINDING_24; 19/38 → FINDING_25; 20/36 → FINDING_26; 6/46 → FINDING_8; 9/15/34/49 → OOS_2; 13/25/30 → FINDING_12; 14/33 → FINDING_14; 41 stands alone as FINDING_3 (also overlaps FINDING_30 doc drift). Highest-priority in-scope cluster for release cut viability: **FINDING_3** (live baseline), **FINDING_1** + **FINDING_2** (harness green), then **FINDING_10**, **FINDING_11**, **FINDING_17**–**FINDING_19** (operator/security/idempotency).

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

