### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Asymmetric retry depth (ship-pr two-pass vs review-and-fix one follow-up)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ship-pr` may run two pre-rebase fixup passes while round mode has only one follow-up; hook re-dirties on every commit can leave residue and `applied` long before rebase Option A runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add second follow-up in round mode or enforce earlier tracked cleanup before push.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `run_rebase_rebump` auto-commits all dirty tracked files before drop-bump
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Partial or unreviewed tracked edits can be silently committed under a generic chore subject and proceed toward rebase/force-push instead of stalling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Log staged paths; restrict fixup paths or run checks before push; stall when fixup touches non-log paths.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Follow-up commit does not re-run submodule revert/scrub
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A hook re-touching submodule paths after primary revert could allow submodule changes into the follow-up commit when staging with `git add -A` or broad adds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Re-run submodule revert before follow-up or stage with git add -u excluding submodule paths.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: No test for staged-only dirty tree at rebase drop site
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `git add -u` / index-only dirty state could skip fixup while porcelain guard still fires, causing stall without regression signal in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add staged-only fixture and assert fixup commit + exit 0.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Rebump version-fixture setup duplicated in tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: ~130 lines of rebump version-fixture setup duplicate `rebump_changelog_commit_shape`, increasing maintenance and copy-paste risk when bump/changelog fixtures change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract _make_rebump_version_fixture helper parameterized by version and optional dirty file.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `rebump_fixup_commit_fail_stalls` omits stale bump on branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Test validates Guard 1 dirty-tree stall only, not the combined stale-bump + dirty-tree production scenario from #3208.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reuse bump-on-branch setup from rebump_dirty_tracked_fixup; stub git-commit.sh fixup failure only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: `rebump_fixup_commit_fail_stalls` fragile log grep assertions
- **Reviewer(s)**: dyn-stall-exit-code-trace-output.txt
- **Severity**: important
- **Concern**: Exit 4 / `STALL_STEP=10` are reachable and correct, but the follow-on grep searches only stdout and the first `ship-pr-fail-rebase-*.log` while fixup failure and Guard-1 text may land in later captures or `execution-issues.md`, so the case can fail `ok` even when stall behavior is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stall-exit-code-trace-output.txt: Drop the fragile dual-grep or scan all `$tmp/ship-pr-fail-rebase-*.log` (and/or `$tmp/execution-issues.md`); keep `assert_rc 4`, `STALL_STEP=10`, `EXIT_CODE=4`, and optionally stdout `⛔ ship-pr: stalled at step 10`.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `make lint` / relevant-checks not verified for merge
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Reviewer did not run `bash scripts/relevant-checks.sh`; merge may fail CI or pre-commit despite plan-complete implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Run bash scripts/relevant-checks.sh before merge.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Option A pre-rebase fixup needs multi-pass hook handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Pre-rebase fixup in `ship-pr.sh` is single-pass; pre-commit hooks can re-dirty the tree after the fixup commit (same class as Option B hook tests). One pass can leave tracked porcelain non-empty so `drop-bump-commit` Guard 1 returns `DROPPED=false` and `exit_stall` 10 (#3209 failure class at rebase time).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a two-pass fixup loop (as in local working-tree edits), document in ship-pr.md, and add a rebump test with a pre-commit hook.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated dirty-tree commit logic across ship-pr and review-and-fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Dirty-tree commit logic is duplicated in `ship-pr.sh` and `review-and-fix.sh` with diverging `git add` flags and pass counts. Future fixes at one site (multi-pass, staging scope) may not propagate, reintroducing stalls or inconsistent commit contents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep staging flags aligned within each script; extract a shared helper if a third callsite appears.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Pre-rebase fixup `continue` on empty index with dirty porcelain
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `git add -u` leaves an empty index but porcelain remains dirty (e.g. skip-worktree or unstagable tracked state), the loop continues through both passes and still hits drop-bump Guard 1 stall without fixup context; Option A may not improve over single-pass stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Break after no-op pass or document; optional early warning
  - From cursor-specialist-edge-cases-output.txt: Log unstagable residue; consider one git add -A attempt or explicit operator message before drop-bump.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: `ship-pr.md` omits two-pass pre-rebase fixup loop
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Documentation describes single-pass pre-rebase fixup while implementation (including uncommitted two-pass loop) can run two passes when hooks re-dirty after the first fixup commit; operators miss the behavior when diagnosing duplicate fixup commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document two-pass behavior per ship-pr.sh:2856-2875
  - From cursor-specialist-edge-cases-output.txt: Update ship-pr.md to describe two-pass hook handling.
  - From cursor-specialist-plan-fidelity-output.txt: Document the two-pass loop in ship-pr.md or revert to single-pass if minimal plan scope is required.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

