## Plan

Fix the spurious `run_rebase_rebump` stall two ways (Option A + B), without changing `drop-bump-commit.sh` or its guards.

- **Option A (catch-all at the stall site):** in `ship-pr.sh` `run_rebase_rebump`, commit leftover tracked files before `drop-bump-commit.sh` so Guard 1 cannot fire on a dirty tree.
- **Option B (root-cause hardening):** in `review-and-fix.sh` round mode, re-check the tracked tree after the round commit and commit once more if a pre-commit hook re-dirtied it.

### UPDATED: `scripts/ship-pr.sh`
Option A. In `run_rebase_rebump`, between the existing `refresh-run-logs.sh` pre-flush (around line 2851) and the `drop-bump-commit.sh` invocation (around line 2858), add a "commit pre-rebase tracked leftovers" step:

- Guard: `if [[ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]]; then` — fires only when tracked files are dirty (same scope as `drop-bump-commit.sh` Guard 1). Clean tree → no-op.
- Stage tracked-only: `git add -u` (modified + deleted tracked files; untracked excluded). Capture to a `failure_capture_path rebase` file.
- Commit when staged: mirror the existing CI-fix shape at lines 1806–1813 — `if ! git diff --cached --quiet 2>/dev/null; then "$SCRIPT_DIR/git-commit.sh" -m "chore: pre-rebase working-tree fixup (#3209)" ...; fi`.
- Best-effort failure handling: on `git add -u` or `git-commit.sh` non-zero, `record_failure rebase "<step>" "$rc" "$fail_file" Warnings` and **fall through** to `drop-bump-commit.sh`. If the leftovers cannot be committed, Guard 1 still stalls exactly as today — Option A can only improve, never regress.
- The commit message must NOT match `^Bump version to [0-9]+\.[0-9]+\.[0-9]+$` or `Update CHANGELOG for ` so the bump/changelog drop helpers do not treat the fixup as a bump/changelog commit.
- Do NOT touch the `DROPPED=false` stall block (lines 2865–2875) or `drop_bump_no_matching_commit`; the genuine stale-bump protection (#2852) and the no-matching-commit no-op stay intact.

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.sh`
Option B. In `apply_findings_with_coder`, insert the residue re-check **after `commit_sha=$(git rev-parse HEAD ...)` at line 460 and before the `fi` at line 461 that closes the `round_num > 0` branch (437–461)**. Do NOT anchor on line 464 — lines 462–464 are the shared path / success block OUTSIDE the branch; inserting there would run the follow-up in findings mode too and break round-mode-only scope.

- Re-check tracked residue: `if [[ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]]; then`. This fires when a pre-commit hook re-modified tracked files after staging (hook edits are not re-staged, so they survive the round commit as a dirty tree).
- `set -euo pipefail` safety: `review-and-fix.sh` runs `set -euo pipefail` (line 4), so the follow-up `git add -A` / `git-commit.sh` MUST be guarded — bare commands would abort the script and skip the warn-and-continue path. Use a condition list mirroring the guarded primary block (438–459): `if git add -A 2>>"$round_dir/coder-commit.log" && "$PLUGIN_ROOT/scripts/git-commit.sh" -m "Address code review feedback (round $round_num) — follow-up" >>"$round_dir/coder-commit.log" 2>&1; then commit_sha=$(git rev-parse HEAD 2>/dev/null || true); else larch_err "..."; fi`.
- One-shot only (no loop): after the follow-up, re-check once more; if still dirty, `larch_err` warn and continue. Do NOT loop — a non-idempotent hook would spin; Option A backstops at the ship-pr drop site.
- Scope guard: keep this strictly inside the `round_num > 0` branch (437–461). Findings mode (no `round_num`) still defers the commit to the parent caller — unchanged.

### UPDATED: `scripts/test-ship-pr.sh`
Add one offline regression test for Option A, reusing the existing `run_rebase_rebump` fixture style (real git + real `drop-bump-commit.sh`/`git-commit.sh`, as at lines 2411–2495):

- Set up a branch with a `Bump version to X.Y.Z` commit on top, then leave one tracked file modified-but-uncommitted in the working tree.
- Drive `ship-pr.sh` through the phase that fires `run_rebase_rebump` on `ACTION=rebase` (same trigger as the `ci-initial` test at lines 2385–2402).
- Assert: ship-pr exits 0 (no `exit_stall 10`/`12`), the dirty tracked file is now committed (a `chore: pre-rebase working-tree fixup` commit exists), and the bump was dropped + re-bumped.

### UPDATED: `skills/review-and-fix/scripts/test-review-and-fix.sh`
Add one offline regression test for Option B using the **round-mode orchestrator harness** — `run_orchestrator_case` / `run_review_and_fix ... --mode diff --round-num 1` (around lines 336–361), which drives the real `git add -A` + `git-commit.sh` path through `apply_findings_with_coder`. Do NOT call `apply_findings_with_coder` directly, and do NOT use the findings-mode setup (303–324) as the round-mode template (`make_work_repo` is 263–271).

- Install a `.git/hooks/pre-commit` in the work repo (built by `make_work_repo`) that re-modifies one tracked file on its first run and is idempotent thereafter, so `git-commit.sh`'s `git commit` triggers it and leaves tracked residue after the round commit.
- Drive a round-mode case (stub coder edits a tracked file, `--round-num 1`).
- Assert: after the round, `git status --porcelain --untracked-files=no` is empty, a follow-up commit exists on top of the `Address code review feedback (round 1)` commit, and `CODER_COMMIT_SHA` points at the latest (follow-up) commit.

### UPDATED: `scripts/ship-pr.md`
Document the Option A pre-rebase tracked-leftover fixup commit in `run_rebase_rebump` (purpose, tracked-only scope, best-effort fall-through, #3209 reference).

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.md`
Document the Option B round-mode post-commit completeness re-check (pre-commit-hook re-dirty case, one-shot follow-up, round-mode-only scope, #3209 reference).

### Approach
Defense in depth. Option A makes `run_rebase_rebump` self-healing for any dirty-tracked-tree precondition regardless of source (recovery agent, hook, or timing window) — this alone fixes the reported stall. Option B removes the most likely upstream source (a pre-commit hook leaving tracked files dirty after the round commit). Both reuse `git-commit.sh` and the existing `git status --porcelain --untracked-files=no` idiom; no new flags, scripts, or abstractions. Commit (not stash): popping a stash after `git rebase --onto` or the rebase onto main can conflict; committing replays the leftovers cleanly.

### Edge cases
- Clean tree at the drop site → Option A no-op (common case).
- Only staged changes (worktree clean, index dirty) → `git add -u` no-op but `git diff --cached --quiet` false → fixup commit still lands.
- Deleted tracked files → `git add -u` stages the deletions.
- New untracked files → excluded by both fixes (`--untracked-files=no`); Guard 1 already ignores them.
- Option B normal case (clean tree) → re-check no-op; `CODER_COMMIT_SHA` unchanged.
- Option B findings mode (no `round_num`) → block skipped; parent-owned commit unchanged.

### Failure modes
1. Option A fixup commit fails → recorded as a Warning; fall through to `drop-bump-commit.sh`, which stalls via Guard 1 exactly as before (no regression).
2. Non-idempotent pre-commit hook in Option B → tree still dirty after the single follow-up; `larch_err` warns; no loop; Option A backstops at the ship-pr drop site.
3. Fixup commit alters bump classification → the leftover changes are legitimately part of the branch and should count; the distinct commit subject avoids the bump/changelog drop regexes.

## Acceptance

- `ship-pr.sh run_rebase_rebump` no longer stalls when the working tree has uncommitted tracked changes at the drop site: a `chore: pre-rebase working-tree fixup` commit is created, `drop-bump-commit.sh` drops the bump, and the rebase+re-bump proceeds.
- The existing `DROPPED=false` stall for genuine stale-bump risk and the no-matching-commit no-op are preserved unchanged; `drop-bump-commit.sh` and `test-drop-bump-commit.sh` are not modified.
- `review-and-fix.sh` round mode never returns `CODER_STATUS=applied` with uncommitted tracked changes: the guarded one-shot follow-up commit captures pre-commit-hook residue (set -e safe); findings mode is unchanged.
- New `test-ship-pr.sh` case (dirty tree → no stall + fixup commit + bump re-bumped) passes.
- New `test-review-and-fix.sh` case (hook re-dirties tracked file in round mode → clean tree + follow-up commit + `CODER_COMMIT_SHA` is the follow-up) passes.
- `make lint` / `bash scripts/relevant-checks.sh` clean repo-wide.
- Doc siblings `scripts/ship-pr.md` and `skills/review-and-fix/scripts/review-and-fix.md` updated in the same change.

diff_lines: 190
