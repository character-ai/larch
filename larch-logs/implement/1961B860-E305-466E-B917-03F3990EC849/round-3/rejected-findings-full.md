### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: `rebump_hook_redirty_second_fixup` allows ≥2 fixups without content checks
- **Reviewer(s)**: dyn-test-fixture-validity-output.txt
- **Severity**: latent
- **Concern**: `fixup_count -ge 2` passes with three or more fixup commits; the test does not verify `initial dirty` / `hook re-dirty` landed in fixup commit(s).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-validity-output.txt: Tighten to `[[ "$fixup_count" -eq 2 ]]` and add a `git log -1 -p --grep='chore: pre-rebase working-tree fixup (#3209)'` (or per-SHA `git show`) check that `sentinel-fix.txt` contains both `initial dirty` and `hook re-dirty`.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: no test for partial multi-file coder commit under Option B
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Option B hook-residue coverage does not exercise the original #3208 partial-commit path (two dirty tracked files, single-file round commit); that path is only indirect via ship-pr Option A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness with two dirty tracked files and single-file round commit if hardening Option B upstream.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: pre-rebase fixup auto-commits all dirty tracked paths before force-push
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Option A `git add -u` + generic chore fixup before rebase/force-push removes the Guard-1 stall that previously forced human inspection. Compromised or buggy agent/local edits confined to the working tree could be bundled into `chore: pre-rebase working-tree fixup` and shipped with less review attention than round feedback commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict fixup staging to an allowlisted path set, or fail closed when dirty paths are outside that set; document that implement reviewers must scan fixup commits on merge PRs.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: missing ship-pr regression tests for add-failure / hook re-dirty / deep bump depth edges
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Gaps remain for add failure with staged index, hook re-dirty, and deep bump depth edge cases—regressions could return without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add tests for those paths or commit existing unstaged cases.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: ship-pr Option A allows only one pre-rebase fixup before drop-bump
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: A single fixup pass cannot recover when `git-commit.sh` / pre-commit re-dirties tracked files during the fixup commit. Porcelain stays dirty at drop-bump Guard 1; `DROPPED=false` stall at step 10/12 persists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Run up to two fixup passes or re-check porcelain after each fixup commit.
  - From cursor-specialist-correctness-output.txt: Second fixup pass when porcelain remains after first (or hook-safe commit path)
  - From cursor-specialist-testing-output.txt: Up to two fixup passes and increase drop-bump --max-depth by fixup count; add hook re-dirty rebump harness.
  - From cursor-specialist-edge-cases-output.txt: Allow a second fixup pass when porcelain remains after the first.
  - From cursor-specialist-plan-fidelity-output.txt: Add second fixup pass and depth bump (as in unstaged WIP) or document as known residual risk.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: fixup commits do not increase drop-bump `--max-depth`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Each fixup commit increases distance to the bump commit without widening the drop walk. On deep histories (bump at HEAD~20+), drop-bump can miss the bump; `DROPPED=false` / stale bump on force-push risk persists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass --max-depth 20 + fixup_count (capped) to drop-bump and changelog drop helpers.
  - From cursor-specialist-edge-cases-output.txt: Bump --max-depth by fixup_commit_count (capped) for drop-bump and drop-changelog.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: ship-pr pre-rebase fixup does not revert dirty submodule paths before staging
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-git-add-scope-output.txt
- **Severity**: latent
- **Concern**: Option A stages with `git add -u` but does not revert submodule-root / gitlink dirt before staging (unlike round commit handling in `review-and-fix.sh`). Dirty submodule state can be committed into `chore: pre-rebase working-tree fixup`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Revert submodule-root paths before git add -u (mirror CI-fix rollback semantics).
  - From cursor-specialist-edge-cases-output.txt: Revert submodule dirt before staging (mirror review-and-fix submodule handling).
  - From dyn-git-add-scope-output.txt: Reuse the same submodule revert helper pattern as `post_dispatch_submodule_revert` / uncommitted `ship_pr_revert_submodule_dirty_paths` before `git add -u`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: review-and-fix follow-up does not re-run submodule revert before staging
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: latent
- **Concern**: The follow-up path runs `git add -A` without `post_dispatch_submodule_revert`. Submodule-related tracked residue (or hooks re-touching submodule paths) can re-stage content the primary revert deliberately removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-add-scope-output.txt: Call `post_dispatch_submodule_revert` before follow-up staging; on `revert_count > 0`, return `submodule-violation` as on the primary path (as in the uncommitted working-tree version at `461-495`).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

