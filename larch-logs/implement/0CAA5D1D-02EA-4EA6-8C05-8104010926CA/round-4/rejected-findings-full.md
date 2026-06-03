### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: release-prepare --bump override duplicates classify-bump arithmetic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` applies `--bump major|minor|patch` via an inline semver increment `case` block (lines 259–270) instead of delegating to `classify-bump.sh`. If either block changes independently, operator overrides can produce a different `NEW_VERSION` than the classifier for the same `CURRENT_VERSION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: CHANGELOG rebase conflicts routed to external vendors with full hunks
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After deleting `auto-resolve-changelog.sh` and removing `CHANGELOG*` from the non-bump-only vendor conflict classifier (`scripts/ship-pr.sh` roughly 2481–2788), `CHANGELOG.md` rebase conflicts on branches rebasing onto mains that still have changelog history are no longer auto-resolved locally. They enter the vendor conflict path (Codex/Cursor) with full hunks—raising stall rate on legacy branch shapes and potentially exposing sensitive release-note text externally. Related routing change: dropping CHANGELOG basename exclusion from `ship_pr_vendor_conflict_csv_is_non_bump_only` alters CI-fix conflict classification vs pre-Phase-5 behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Stale `run_rebase_rebump` name after rebump removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` still names the CI-fix rebase helper `run_rebase_rebump` (lines 2646–2894) though rebump/version logic was removed. Grep and readers can misread the flow as still re-bumping versions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Stale `ship_pr_vendor_conflict_csv_is_non_bump_only` identifier
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The function name `ship_pr_vendor_conflict_csv_is_non_bump_only` (lines 2481–2536) still encodes bump/changelog semantics removed in Phase 5. New contributors grepping `non_bump` may assume CHANGELOG/bump routing still exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `RebaseResult.new_version` is always None in Python port
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/rebase.py` (lines 25–32) defines `RebaseResult.new_version` but never populates it. Callers and tests carry dead surface area for the Phase 7 port.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

