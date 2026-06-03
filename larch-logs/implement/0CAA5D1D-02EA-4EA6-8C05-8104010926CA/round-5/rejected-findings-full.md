### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: verify-skill-called 5b accepts nonnumeric count_commits output
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-verify-skill-called.sh` section 5b only checks that sourcing from `/tmp` emits output, not that `count_commits` returns a numeric count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_15: Rebase prepass no longer auto-resolves CHANGELOG conflicts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/ship-pr.sh` no longer auto-resolves CHANGELOG conflicts during feature-branch rebase, so branches rebasing onto upstream CHANGELOG changes may stall or route to the wrong conflict path instead of the former silent prepass fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: classify-bump --head does not require HEAD OID equality
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/classify-bump.sh --head` can accept a version match without verifying that `HEAD` equals `HEAD_COMPARE`, allowing direct `--head-only` use to classify the wrong commit tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: subskill invocation docs misstate /implement and /release relationship
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/shared/subskill-invocation.md` contains stale Phase 1/5 wording suggesting `/implement` no longer nests or gates `/release`, rather than accurately saying per-PR bump/CHANGELOG gates were removed from the ship path and `/release` remains the external versioning path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: RebaseResult exposes always-empty new_version field
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/rebase.py` keeps `RebaseResult.new_version` as a public dataclass field even though it is always `None`, inviting future Python ship code to branch on a rebump result that no longer exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: classify-bump semver formatting misses full 10# normalization
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/classify-bump.sh` does not apply `10#` normalization to all MINOR/PATCH semver components, so rare leading-zero inputs could produce inconsistent `NEW_VERSION` formatting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: ship-pr rebase test under-pins removed bump/changelog symbols
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-ship-pr-rebase.sh` pins classify-bump absence but not other deleted changelog/rebump basenames or call sites, so reintroducing removed prepass logic may not fail the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

