## Decision 1: Fix surfaces (in/out of scope)
- **Question**: Which of issue #3209's three fix options should this design implement?
- **Resolution**: Option A + B. (A) Guard the drop site in `ship-pr.sh` `run_rebase_rebump`; (B) harden `review-and-fix.sh` so the round-mode coder commit never returns with uncommitted tracked changes. Option C (`--allow-dirty` flag in `drop-bump-commit.sh`) is explicitly OUT of scope — it mutates a guarded narrow primitive and risks stash-pop conflicts.
- **Source**: user

## Decision 2: Option A mechanism — commit vs stash
- **Question**: When `run_rebase_rebump` finds a dirty tracked tree before the drop, should it commit the leftovers or stash-then-pop?
- **Resolution**: Commit the leftover tracked files as a real branch commit. The commit replays cleanly during the subsequent `rebase-push.sh` onto main and the changes are never lost. Stash/pop is rejected: popping after `git rebase --onto` (the drop) or after the rebase onto main can conflict against the rewritten tree.
- **Source**: codebase (drop-bump-commit.sh uses `git reset --hard` / `git rebase --onto`; ship-pr.sh rebases onto main right after the drop)

## Decision 3: Option A staging scope — tracked-only vs all
- **Question**: Should the Option A fixup commit stage tracked files only, or everything including untracked?
- **Resolution**: Tracked-only (`git add -u` semantics), matching Guard 1's `git status --porcelain --untracked-files=no` scope. Untracked artifacts (e.g. larch-logs) are owned by `refresh-run-logs.sh` (already flushed at ship-pr.sh:2849) and the snapshot/commit machinery; they must not be swept into a pre-rebase source fixup.
- **Source**: codebase (drop-bump-commit.sh Guard 1 is `--untracked-files=no`)

## Decision 4: Preserve the genuine stale-bump stall (hard constraint)
- **Question**: Must the existing `DROPPED=false` stall (ship-pr.sh:2872, the #2852 silent-stale-bump protection) be preserved?
- **Resolution**: Yes — hard constraint. Option A only clears the dirty-tree precondition *before* `drop-bump-commit.sh` runs. The `DROPPED=false` stall for genuine stale-bump reasons, and the `drop_bump_no_matching_commit` no-op path, stay exactly as they are. After the fixup commit, `drop-bump-commit.sh` is still invoked normally.
- **Source**: codebase

## Decision 5: Option B scope — round mode only
- **Question**: Should Option B's completeness guarantee also cover findings mode (standalone `/review --diff`)?
- **Resolution**: Round mode only — the `/implement` Step 5 path where `review-and-fix.sh` owns the commit (`apply_findings_with_coder` with `round_num`). Findings mode (no `round_num`) deliberately defers the commit to the parent caller (review-and-fix.sh:434–436) and stays out of scope.
- **Source**: codebase

## Decision 6: Root-cause shape for Option B
- **Question**: Why does the round-mode commit (`git add -A` + `git-commit.sh`) leave tracked files dirty?
- **Resolution**: `git add -A` stages everything and `git-commit.sh` commits all staged content, so the leak is not selective staging. The residual-dirty case is a **pre-commit hook re-modifying tracked files after staging** (the hook's edits are not re-staged, so they survive the commit as a dirty tree). Option B re-checks `git status --porcelain --untracked-files=no` after the commit and re-stages + commits once more if tracked changes remain.
- **Source**: codebase (git-commit.sh runs `git commit` without `--no-verify`; repo has pre-commit hooks)

## Decision 7: What proves done
- **Question**: What is the verification bar?
- **Resolution**: Extend the offline harnesses — `scripts/test-ship-pr.sh` (dirty-tree fixup-before-drop in `run_rebase_rebump`) and `skills/review-and-fix/scripts/test-review-and-fix.sh` (round-mode post-commit completeness). `make lint` / `bash scripts/relevant-checks.sh` clean. No change to `drop-bump-commit.sh` behavior or its harness.
- **Source**: codebase
