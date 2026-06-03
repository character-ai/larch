### OOS_1: [OUT_OF_SCOPE] `apply-bump.sh` `semver_lt` lacks `10#` coercion
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply-bump` `semver_lt` lacks `10#` coercion used in new release scripts. Inconsistent octal-edge behavior across bump paths (pre-existing). Align when consolidating semver helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Legacy `promote-latest-release.sh` retained
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Legacy `promote-latest-release.sh` remains alongside the new cut-a-release flow. Operators might invoke the old promote-only path by habit. Remove after migration if unused.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `merge-pr.sh` never fetches after successful merge
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `merge-pr.sh` never fetches after a successful merge. Downstream scripts expecting fresh `origin/main` or merge-OID objects may fail until manual fetch. Add optional post-merge `git fetch origin main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Harness fixtures use wrong `is_latest` API shape
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Offline `test-release-prepare` fixtures use `is_latest` on `gh api` shape while production lacks that field, so CI cannot catch FINDING_7. Add cases with `gh release list` JSON field names or integration smoke against real `gh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] `release-tag.yaml` still builds notes from `CHANGELOG.md`
- **Reviewer(s)**: dyn-tag-release-race-output.txt
- **Severity**: nit
- **Concern**: When the workflow wins the release-creation race, notes come from `CHANGELOG.md` until `/release` overwrites via `gh release edit`. Pre-existing overlap, not introduced by core helpers on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tag-release-race-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Plan vs `release-finish.md` documentation drift on fallback
- **Reviewer(s)**: dyn-tag-release-race-output.txt
- **Severity**: nit
- **Concern**: Implementation plan still describes `mergeCommit` with `origin/main` fallback; branch dropped fallback in round 1. Documentation drift only; behavior is defined by script and contract file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tag-release-race-output.txt: Address the concern above.

---

**Merge summary (for voters):** 49 raw inputs → **30 in-scope** findings + **6 out-of-scope**. Highest-impact clusters: **FINDING_7** (baseline API field), **FINDING_8–9** (post-merge git handoff), **FINDING_14–16** (harness gaps), **FINDING_19–20** (fail-open guards / partial promote). Code read confirms `is_latest` at ```108:108:.claude/skills/release/scripts/release-prepare.sh``` and `git show` without prior fetch at ```153:156:.claude/skills/release/scripts/release-finish.sh```.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

