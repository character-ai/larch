### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: test-release-set-version lacks jq-failure atomicity test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test covers `jq` rewrite failure; partial write or tmp leak on jq error may not be caught by cmp-on-rejection tests alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fake jq failure in PATH; assert plugin.json unchanged via cmp.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: PR numbers from git log not verified merged in window
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: PR numbers are parsed from squash-merge subjects via `(#N)` without verifying `gh pr view` refers to a PR actually merged in the baseline..HEAD window; commit subjects on `main` could skew public release notes toward arbitrary PR metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Cross-check each PR’s `mergedAt` / merge commit SHA against the `git log` range, or use `gh pr list --search` anchored to the baseline..HEAD SHAs.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: release-finish.sh --pr not validated as numeric
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--pr` is not validated as a numeric PR id before `gh pr view`; quoting prevents shell injection but bad orchestrator input fails late.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: validating `^[0-9]+$` would fail fast on orchestrator mistakes.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `--bump` override duplicates classify-bump increment logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `--bump` override in `release-prepare.sh` reimplements semver increment logic already in `classify-bump.sh`, so future bump rule changes require editing two places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reuse classify-bump or shared `_apply_bump_type` helper for override recompute.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: semver_lt duplicated from apply-bump.sh (DRY drift risk)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `semver_lt` in `release-set-version.sh` duplicates logic from `apply-bump.sh`; semver comparison semantics can drift across bump/release scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared semver helper if more callers appear.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

