Structured aggregator output from the supplied reviewer findings (merged by behavioral risk; verbatim revision bullets preserved where reviewers gave concrete direction).

### FINDING_1: review-and-fix follow-up stages with `git add -A` while residue detection is tracked-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-git-add-scope-output.txt
- **Severity**: important
- **Concern**: Follow-up residue checks use `git status --porcelain --untracked-files=no`, but follow-up staging uses `git add -A`. When tracked hook residue coexists with untracked review artifacts, follow-up can commit untracked paths even though only tracked dirt triggered the path—broader than Guard 1 / Option A tracked-only intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use git add -u for follow-up or exclude untracked before staging
  - From cursor-specialist-testing-output.txt: Use git add -u for follow-up staging.
  - From cursor-specialist-edge-cases-output.txt: Use git add -u (and submodule revert before staging) for the follow-up pass.
  - From dyn-git-add-scope-output.txt: Use `git add -u` for the follow-up (aligned with Option A and the updated doc at `skills/review-and-fix/scripts/review-and-fix.md:56`).

### FINDING_2: review-and-fix follow-up leaves `CODER_STATUS=applied` / exit 0 when tracked porcelain remains
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-git-add-scope-output.txt
- **Severity**: important
- **Concern**: After follow-up (or on follow-up failure), tracked residue only warns while the script still emits `CODER_STATUS=applied` and returns 0. `/implement` Step 5 treats the round as successfully applied; `ship-pr` may proceed until drop-bump Guard 1 or dirty-tree guards surface the dirty tree (non-idempotent pre-commit hooks are a primary trigger).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Emit CODER_STATUS=failed and return 2 when follow-up fails or tracked porcelain remains.
  - From cursor-specialist-correctness-output.txt: Emit CODER_STATUS=failed and return 2 when porcelain remains after follow-up (fail-closed per acceptance)
  - From cursor-specialist-testing-output.txt: On still-dirty after follow-up set CODER_STATUS=failed and return 2; add persistent-hook harness expecting non-zero exit.
  - From cursor-specialist-edge-cases-output.txt: After follow-up, if tracked porcelain is non-empty emit CODER_STATUS=failed and return 2.
  - From cursor-specialist-plan-fidelity-output.txt: Return exit 2 / CODER_STATUS=failed when post-follow-up git status --porcelain --untracked-files=no is non-empty, or update plan acceptance to match warn-and-continue.
  - From dyn-git-add-scope-output.txt: Fail closed: `CODER_STATUS=failed`, `return 2`, when `git status --porcelain --untracked-files=no` is still non-empty after follow-up (as in the uncommitted working-tree block at `498-508`).

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

### FINDING_4: ship-pr pre-rebase fixup skips commit when `git add -u` fails despite non-empty index
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-git-add-scope-output.txt
- **Severity**: important
- **Concern**: The fixup path chains `git add -u` and commit via `if`/`elif`, so a failed `git add -u` skips `git-commit.sh` even when the index already holds staged tracked changes (“index dirty, worktree clean”). Staged-only dirt remains uncommitted; drop-bump Guard 1 still stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Record add failure as Warning but still attempt git-commit.sh when the index is non-empty.
  - From cursor-specialist-correctness-output.txt: Decouple add failure from commit attempt; commit when git diff --cached is non-empty
  - From cursor-specialist-testing-output.txt: Attempt git-commit.sh whenever index is non-empty regardless of git add -u rc.
  - From cursor-specialist-edge-cases-output.txt: Decouple add failure recording from commit: attempt git-commit.sh whenever git diff --cached is non-empty.
  - From dyn-git-add-scope-output.txt: Match the CI-fix pattern at `scripts/ship-pr.sh:1875-1880` and the local `ship_pr_pre_rebase_fixup_pass` helper: record a warning on `git add -u` failure, then always try `git-commit.sh` when `git diff --cached` is non-empty.

### FINDING_5: fixup commits do not increase drop-bump `--max-depth`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Each fixup commit increases distance to the bump commit without widening the drop walk. On deep histories (bump at HEAD~20+), drop-bump can miss the bump; `DROPPED=false` / stale bump on force-push risk persists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass --max-depth 20 + fixup_count (capped) to drop-bump and changelog drop helpers.
  - From cursor-specialist-edge-cases-output.txt: Bump --max-depth by fixup_commit_count (capped) for drop-bump and drop-changelog.

### FINDING_6: ship-pr pre-rebase fixup does not revert dirty submodule paths before staging
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-git-add-scope-output.txt
- **Severity**: latent
- **Concern**: Option A stages with `git add -u` but does not revert submodule-root / gitlink dirt before staging (unlike round commit handling in `review-and-fix.sh`). Dirty submodule state can be committed into `chore: pre-rebase working-tree fixup`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Revert submodule-root paths before git add -u (mirror CI-fix rollback semantics).
  - From cursor-specialist-edge-cases-output.txt: Revert submodule dirt before staging (mirror review-and-fix submodule handling).
  - From dyn-git-add-scope-output.txt: Reuse the same submodule revert helper pattern as `post_dispatch_submodule_revert` / uncommitted `ship_pr_revert_submodule_dirty_paths` before `git add -u`.

### FINDING_7: review-and-fix follow-up does not re-run submodule revert before staging
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: latent
- **Concern**: The follow-up path runs `git add -A` without `post_dispatch_submodule_revert`. Submodule-related tracked residue (or hooks re-touching submodule paths) can re-stage content the primary revert deliberately removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-add-scope-output.txt: Call `post_dispatch_submodule_revert` before follow-up staging; on `revert_count > 0`, return `submodule-violation` as on the primary path (as in the uncommitted working-tree version at `461-495`).

### FINDING_8: review-and-fix.md disagrees on round commit ownership / follow-up staging
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Adjacent documentation paragraphs disagree on where round commits happen and describe `git add -A` for follow-up vs tracked-only / fail-closed behavior—operators may misread orchestrator vs in-function commit ownership.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate round-mode commit documentation into one accurate paragraph.
  - From cursor-specialist-edge-cases-output.txt: Update doc to git add -u and fail-closed behavior.

### FINDING_9: missing test for persistent hook residue after follow-up (exit 2 / `CODER_STATUS=failed`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No harness asserts that persistent post-follow-up tracked hook residue yields non-zero exit and `CODER_STATUS=failed`; regression could restore warn-and-continue `applied` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add persistent-hook case asserting exit 2 / CODER_STATUS=failed
  - From cursor-specialist-testing-output.txt: On still-dirty after follow-up set CODER_STATUS=failed and return 2; add persistent-hook harness expecting non-zero exit.

### FINDING_10: `rebump_dirty_tracked_fixup` does not prove drop/rebump or fixup content
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-fixture-validity-output.txt
- **Severity**: important
- **Concern**: The case greps log subjects (`chore: pre-rebase…`, `Bump version to 1.2.4`) but does not assert the stale bump was dropped, that drop-bump ran (`DROPPED=true`), or that the seeded dirty content (`dirty tracked residue` in `sentinel-fix.txt`) appears in the fixup commit—wrong bump stacking or wrong dirt could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert final plugin.json 1.2.4 HEAD bump only; optionally assert DROPPED=true or no stall stdout.
  - From cursor-specialist-plan-fidelity-output.txt: Assert Bump version to 1.2.3 absent from recent log or DROPPED=true from drop-bump in fixture output.
  - From dyn-test-fixture-validity-output.txt: Resolve the fixup commit SHA (e.g. `git log --format=%H --grep='chore: pre-rebase working-tree fixup (#3209)' -n 1`) and assert `git show "$sha":sentinel-fix.txt` contains `dirty tracked residue`, mirroring the content-level assertion in the plan acceptance criteria.

### FINDING_11: `rebump_hook_redirty_second_fixup` allows ≥2 fixups without content checks
- **Reviewer(s)**: dyn-test-fixture-validity-output.txt
- **Severity**: latent
- **Concern**: `fixup_count -ge 2` passes with three or more fixup commits; the test does not verify `initial dirty` / `hook re-dirty` landed in fixup commit(s).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-validity-output.txt: Tighten to `[[ "$fixup_count" -eq 2 ]]` and add a `git log -1 -p --grep='chore: pre-rebase working-tree fixup (#3209)'` (or per-SHA `git show`) check that `sentinel-fix.txt` contains both `initial dirty` and `hook re-dirty`.

### FINDING_12: round-mode hook-residue test lacks commit-count and content assertions
- **Reviewer(s)**: dyn-test-fixture-validity-output.txt
- **Severity**: latent
- **Concern**: The test infers a single follow-up via `HEAD~1` and subject grep but does not assert exactly two commits after init (primary + one follow-up) or that `hook residue` appears in the follow-up commit’s `src/main.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-validity-output.txt: Capture `initial_head` before the run, assert `git rev-list --count "${initial_head}..HEAD" -eq 2`, and `git show HEAD:src/main.py | grep -Fq 'hook residue'` (or equivalent diff against the primary commit).

### FINDING_13: no test that failed pre-rebase fixup still stalls via Guard 1
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Fixup failure path regression could be broken without CI catching it (plan gap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub git-commit.sh failure with dirty tree; expect stall exit 4.

### FINDING_14: no test for partial multi-file coder commit under Option B
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Option B hook-residue coverage does not exercise the original #3208 partial-commit path (two dirty tracked files, single-file round commit); that path is only indirect via ship-pr Option A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness with two dirty tracked files and single-file round commit if hardening Option B upstream.

### FINDING_15: pre-rebase fixup auto-commits all dirty tracked paths before force-push
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Option A `git add -u` + generic chore fixup before rebase/force-push removes the Guard-1 stall that previously forced human inspection. Compromised or buggy agent/local edits confined to the working tree could be bundled into `chore: pre-rebase working-tree fixup` and shipped with less review attention than round feedback commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict fixup staging to an allowlisted path set, or fail closed when dirty paths are outside that set; document that implement reviewers must scan fixup commits on merge PRs.

### FINDING_16: missing ship-pr regression tests for add-failure / hook re-dirty / deep bump depth edges
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Gaps remain for add failure with staged index, hook re-dirty, and deep bump depth edge cases—regressions could return without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add tests for those paths or commit existing unstaged cases.

### OOS_1: [OUT_OF_SCOPE] fixup depth vs drop walk on deep histories (local uncommitted change noted)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Fixup commits without a matching `--max-depth` bump can leave the bump outside the drop walk on deep histories; continue path may force-push a stale bump. Source flags this as tied to local uncommitted depth-bump work rather than the committed diff under review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Increase --max-depth with fixup count (local uncommitted change)

### OOS_2: [OUT_OF_SCOPE] fixup subject does not collide with drop-bump / changelog matchers
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: `chore: pre-rebase working-tree fixup (#3209)` does not match `drop-bump-commit.sh` Guard 2 bump regex or `drop-changelog-commit.sh` exact changelog subject; no collision found for those matchers.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Option A `git add -u` semantics are intentional for staged tracked dirt
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: For modified/deleted tracked files and index-only staged tracked changes, `git add -u` plus cached diff behaves as the plan describes; sweeping pre-existing staged tracked changes into the fixup commit is intentional, not index loss.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] working tree already contains fixes not on reviewed HEAD
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: Uncommitted edits in `scripts/ship-pr.sh` and `skills/review-and-fix/scripts/review-and-fix.sh` reportedly already address submodule revert, decoupled add/commit, `git add -u` follow-up, fail-closed `return 2`, two-pass fixup, and `--max-depth` bump—but those fixes are not on `HEAD` (`65fa13777`); review targeted the committed diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] fixup subject is not a transparent bump-pipeline commit for classify-bump
- **Reviewer(s)**: dyn-git-add-scope-output.txt
- **Severity**: nit
- **Concern**: The fixup subject is not classified as a transparent bump-pipeline commit per `classify-bump.sh`; a fixup above the bump is handled by `drop-bump-commit.sh` replay walk, not mis-identified as the bump commit.
- **Suggested revisions (informational for voters; coder decides)**:
