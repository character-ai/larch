### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Option A commits all dirty tracked paths without allowlist
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-rebase fixup uses blind `git add -u` on every dirty tracked path with a generic chore subject and best-effort fall-through on failure. Partial, off-review, or accidental tracked WIP (agent recovery, hooks, mis-staged fixes) can be committed and rebased without the Step 10 stall that previously forced operator attention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Narrow fixup to an allowlist (e.g. larch-logs), log staged paths before commit, or stall when dirty paths are outside the allowlist.
  - From cursor-specialist-edge-cases-output.txt: Scope staging to implement-known paths or stall when dirty paths are outside an allowlist instead of committing everything tracked.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Option B follow-up auto-commits hook residue without audit trail
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Round-mode follow-up auto-commits tracked hook/tool residue after the primary review commit. Expected for #3209 and bounded by local hook trust, but committed paths are not logged for audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optional: log committed paths in coder-commit.log for audit; no change if hook trust is accepted.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Missing offline tests for staged-only and post-fixup re-dirty rebump edges
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: New rebump/fix-loop tests do not cover Option A with index-only staged tracked residue, nor post-fixup hook re-dirty at the drop-bump site. Regressions in those edge cases (e.g. staged-only skipping fixup and re-triggering drop-bump Guard 1 stalls) would not be caught offline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a fix-loop fixture with staged tracked changes only; assert fixup commit and successful rebump
  - From cursor-specialist-edge-cases-output.txt: Add fixtures for staged-only dirty index and optional pre-commit hook on the fixup commit path.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Happy-path rebump test uses loose subject substring match
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Happy-path rebump test matches fixup/drop subjects by substring rather than commit graph order. Wrong fixup/drop ordering could pass while still breaking rebump invariants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert fixup SHA is ancestor of HEAD and appears before re-bump in git log order


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Option B does not heal partial-file coder commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Option B follow-up only re-dirties tracked files touched by hooks/tools after a full-tree commit; subset commits that leave other tracked paths dirty persist until ship-pr Option A at rebase (same class as prior step 2–3 incidents).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Accept for #3209; optional future guard after coder dispatch if earlier cleanup is needed


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated dirty-tracked commit pattern in ship-pr and review-and-fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The tracked-porcelain → `git add -u` → `git-commit.sh` pattern is duplicated between `scripts/ship-pr.sh` and `skills/review-and-fix/scripts/review-and-fix.sh`, increasing maintenance cost when porcelain or staging semantics change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared helper only if a third call site appears


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicated rebump integration test fixtures
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ship-pr.sh` rebump cases repeat large setup blocks, making the next regression variant harder to add consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared setup helper with parameters for dirty tree and git-commit stub behavior


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

