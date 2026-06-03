### OOS_1: [OUT_OF_SCOPE] promote-release.sh lacks release-prepare Latest uniqueness check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `promote-release` does not fail-closed on multiple `isLatest` unlike `release-prepare`; ambiguous GitHub Latest metadata could promote the wrong release when called outside `/release` prepare guards (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align with release-prepare Latest uniqueness check (pre-existing).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] classify-bump --base operator-controlled refs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--base` passes operator-controlled refs to `git rev-parse` (quoted). Not introduced as a new attack surface beyond existing git usage; `/release` feeds `--base` from `gh`’s `tagName`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Missing test-release-finish / plan harness gap (documentation-only duplicates)
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-bash-compatibility-output.txt, dyn-release-race-conditions-output.txt, dyn-contract-to-implementation-output.txt
- **Severity**: latent
- **Concern**: Multiple reviewers note the plan’s offline `release-finish` fixtures are absent; tagged out-of-scope relative to in-scope FINDING_4 but recorded as pre-existing plan/documentation gap rather than a new runtime defect in this slice alone.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Bash 3.2 portability otherwise sound on release branch
- **Reviewer(s)**: dyn-bash-compatibility-output.txt
- **Severity**: nit
- **Concern**: No `declare -A`/`declare -n`, `${var^^}`, `&>>`, or `${var//…/$replacement}` in new/modified release scripts; `REPO_ARGS=()` pattern matches existing helpers; harness `grep` is piped per `BASH_AUTHORING.md`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Unquoted `for pr in $pr_numbers` acceptable here
- **Reviewer(s)**: dyn-bash-compatibility-output.txt
- **Severity**: nit
- **Concern**: Word-splitting on PR IDs is negligible because IDs are digits-only from `sed`, matching other repo scripts.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] Leading-zero semver in classify-bump.sh predates branch
- **Reviewer(s)**: dyn-bash-compatibility-output.txt
- **Severity**: nit
- **Concern**: Leading-zero arithmetic in `classify-bump.sh:292-296` predates this branch; `release-prepare.sh` duplicates it only for `--bump` override (addressed in-scope by FINDING_23/24).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-compatibility-output.txt: A shared `10#` bump helper would fix both.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] release-finish.sh may not fetch TARGET_OID before git show
- **Reviewer(s)**: dyn-release-race-conditions-output.txt
- **Severity**: latent
- **Concern**: `release-finish.sh` does not `git fetch` the resolved `TARGET_OID` before `git show`; usually fine after `merge-pr.sh`’s fetch, but shallow clones could fail with a less actionable error.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_8: [OUT_OF_SCOPE] classify-bump HEAD vs origin/main equivalence only when guards hold
- **Reviewer(s)**: dyn-contract-to-implementation-output.txt
- **Severity**: latent
- **Concern**: Plan/prepare text describe aggregate classification over `BASELINE_TAG..origin/main`, while `classify-bump.sh --base` still diffs `"$BASE" HEAD`; equivalent only when Step 1’s `main` == `origin/main` guard holds.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

