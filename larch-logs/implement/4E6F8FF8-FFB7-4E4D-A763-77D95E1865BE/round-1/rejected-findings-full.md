### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `keys` mode untested on duplicate and block-boundary fixtures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: At `skills/design/scripts/test-trailer-awk.sh:149-158`, `keys` mode is not asserted on duplicate `diff_added` or block-boundary fixtures. A keys-only emission-order bug could slip past while `values`/`parse` still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Assert keys on duplicate-diff-added (single diff_added) and block-boundary fixtures.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Failed follow-up can fall through to success epilogue (`CODER_STATUS=applied`)
- **Reviewer(s)**: dyn-follow-up-commit-flow-output.txt
- **Severity**: important
- **Concern**: At `skills/review-and-fix/scripts/review-and-fix.sh:467-495`, if the follow-up `if git add -A && git-commit.sh` branch fails but `git status --porcelain --untracked-files=no` is unexpectedly empty afterward, control falls through to the success epilogue: `CODER_STATUS=applied`, exit **0**, and `CODER_COMMIT_SHA` stays at the **primary** round commit SHA even though the follow-up commit never landed. Step 5 can report success while tree state does not match `CODER_COMMIT_SHA`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-follow-up-commit-flow-output.txt: Treat follow-up `else` as failure unless you explicitly verify the residue that triggered the block is gone (e.g. return **2** or at minimum avoid emitting `applied` / refresh `commit_sha` only when follow-up succeeded).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `git add -u` (ship-pr) vs `git add -A` (review-and-fix) staging asymmetry
- **Reviewer(s)**: dyn-follow-up-commit-flow-output.txt
- **Severity**: latent
- **Concern**: Option A pre-rebase fixup (`scripts/ship-pr.sh:2856-2870`) uses `git add -u` (tracked only); round-mode primary and follow-up commits (`skills/review-and-fix/scripts/review-and-fix.sh:438-465`) use `git add -A`. Both gate on tracked-only porcelain (`--untracked-files=no`), but when tracked dirt and new untracked files coexist, Step 5 follow-up can sweep untracked into the follow-up commit while Option A may leave untracked residue and still hit `drop-bump-commit.sh` Guard 1 on a later full-tree check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-follow-up-commit-flow-output.txt: Document the intentional asymmetry and add a harness case with coexisting tracked hook residue plus untracked files, or align staging (`-A` vs `-u`) with the documented “match primary round commit” contract if full staging is required at rebase.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Round-mode follow-up commit lacks second submodule revert after hooks (`review-and-fix.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: At `skills/review-and-fix/scripts/review-and-fix.sh:461-465`, the follow-up round commit uses `git add -A` without re-running submodule revert after pre-commit hooks may rewrite the tree. A hook that re-modifies submodule paths after the first revert/commit can let the follow-up commit record forbidden submodule changes while the round still succeeds until later guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Re-run post_dispatch_submodule_revert before follow-up staging; fail closed on submodule paths in the follow-up index.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Blank-line block boundary not covered in awk unit harness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `skills/design/scripts/test-trailer-awk.sh:103-111`, the plan’s blank-line block boundary is not covered. An awk change treating blank lines as continuations could pass this harness but mis-count `block_len` until integration Case 24 fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a fixture with a blank line between trailers and diff_lines:; assert parse/keys/values/has_key match in-block-only semantics.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

