# Review Round 3

- Mode: `diff`
- 8 accepted, 8 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: review-and-fix follow-up stages with `git add -A` while residue detection is tracked-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-git-add-scope-output.txt
- **Severity**: important
- **Concern**: Follow-up residue checks use `git status --porcelain --untracked-files=no`, but follow-up staging uses `git add -A`. When tracked hook residue coexists with untracked review artifacts, follow-up can commit untracked paths even though only tracked dirt triggered the path—broader than Guard 1 / Option A tracked-only intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use git add -u for follow-up or exclude untracked before staging
  - From cursor-specialist-testing-output.txt: Use git add -u for follow-up staging.
  - From cursor-specialist-edge-cases-output.txt: Use git add -u (and submodule revert before staging) for the follow-up pass.
  - From dyn-git-add-scope-output.txt: Use `git add -u` for the follow-up (aligned with Option A and the updated doc at `skills/review-and-fix/scripts/review-and-fix.md:56`).


### FINDING_10: `rebump_dirty_tracked_fixup` does not prove drop/rebump or fixup content
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-fixture-validity-output.txt
- **Severity**: important
- **Concern**: The case greps log subjects (`chore: pre-rebase…`, `Bump version to 1.2.4`) but does not assert the stale bump was dropped, that drop-bump ran (`DROPPED=true`), or that the seeded dirty content (`dirty tracked residue` in `sentinel-fix.txt`) appears in the fixup commit—wrong bump stacking or wrong dirt could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert final plugin.json 1.2.4 HEAD bump only; optionally assert DROPPED=true or no stall stdout.
  - From cursor-specialist-plan-fidelity-output.txt: Assert Bump version to 1.2.3 absent from recent log or DROPPED=true from drop-bump in fixture output.
  - From dyn-test-fixture-validity-output.txt: Resolve the fixup commit SHA (e.g. `git log --format=%H --grep='chore: pre-rebase working-tree fixup (#3209)' -n 1`) and assert `git show "$sha":sentinel-fix.txt` contains `dirty tracked residue`, mirroring the content-level assertion in the plan acceptance criteria.


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


