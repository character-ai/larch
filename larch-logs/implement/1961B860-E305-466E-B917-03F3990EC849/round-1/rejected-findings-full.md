### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Option B tests cover hook residue only, not partial subset commit path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-review-and-fix.sh` Option B coverage validates hook residue, not the #3208 partial-commit path (partial staging), which is only exercised indirectly via ship-pr Option A. Either simulate partial staging in the stub coder or document hook-only scope in the test.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Option A auto-commits all tracked dirty paths without narrowing or safety gates
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Pre-rebase Option A auto-commits every tracked dirty path before rebase without allowlist, secret scan, or content gates—replacing Guard 1’s fail-closed stall. Malicious or mistaken uncommitted tracked changes (e.g. from a partial coder or recovery agent) can become `chore: pre-rebase working-tree fixup`, proceed through drop/rebump, and reach push with unreviewed content in history. Mitigations: narrow staging (allowlisted paths / known deltas), stall when the dirty set is broader than expected, and optionally run secret/redaction checks before `git-commit.sh`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Option A may skip commit when index empty despite non-empty tracked porcelain
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Option A only runs `git-commit.sh` when `git diff --cached` is non-empty after `git add -u`. Submodule-internal or similar dirty state can yield successful `add -u` with an empty index while porcelain still shows tracked paths; drop-bump Guard 1 then stalls. Should warn with paths, extend staging for remaining tracked paths, or document operator handling.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Option B CI coverage is happy-path only for residue / warn paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `test-review-and-fix.sh` regression coverage for Option B is largely happy-path; follow-up failure, persistent hook dirtiness, and warn/status contract paths are not asserted in CI.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: rebump_dirty_tracked_fixup duplicates large rebump fixture setup
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `rebump_dirty_tracked_fixup` in `scripts/test-ship-pr.sh` duplicates substantial rebump fixture setup already used elsewhere. Future rebump stub edits may require parallel edits in multiple tests; a shared `_setup_rebump_bump_fixture` helper would reduce drift.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Plan / acceptance text vs implemented Option B scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Implemented Option B addresses hook residue only, not a full post-coder completeness scan. Partial Cursor subset commits are not repaired at `review-and-fix`; only at ship-pr rebase (Option A). Issue/acceptance text should align with the plan or `review-and-fix` should be extended if broader Option B was intended.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

