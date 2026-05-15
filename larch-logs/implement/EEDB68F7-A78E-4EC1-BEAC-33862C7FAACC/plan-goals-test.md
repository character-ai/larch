## Goal
Eliminate all post-merge log commits from /implement and /fix-issue runs

## Implementation Plan
## Implementation Plan — Stop post-merge larch log commits

### Goal
After the business PR merges, no git commit or push to main from any larch script.

### Changes

1. **scripts/ship-pr.sh** — write `$IMPLEMENT_TMPDIR/post-merge-sentinel` immediately before `advance_phase postmerge` at every merge-success branch:
   - Line ~995: merged|admin_merged case in run_ci_phase
   - Line ~1010: already_merged detected mid ci-merge phase
   - Line ~1049: already_merged in non-CI path

2. **scripts/larch-log-flush.sh** — add top-of-script exit when sentinel exists (after IMPLEMENT_TMPDIR and LARCH_NO_LOGS_COMMIT checks).

3. **scripts/larch-log.sh** commit subcommand — add loud stderr rejection when $IMPLEMENT_TMPDIR/post-merge-sentinel exists, immediately after arg parsing.

4. **scripts/capture-session-transcript.sh** — remove lines 155-208 (the `if [ "$current_branch" = "main" ]` block: fetch origin/main, validate ahead diff, git push origin main, git reset --hard fallback). The script already commits at lines 147-153; after that it emits `captured`.

5. **scripts/test-capture-session-transcript.sh** — remove push-outcome test scaffolding:
   - Remove helpers: config_git_identity, init_git_repo_main, commit_path, setup_remote_repo, run_capture_in_repo (keep project_dir_for_repo)
   - Remove Step 18 push outcome test cases (push-success, push-fail-abandoned, push-orphan-multi, push-non-flush-diff, fetch-failed)

6. **scripts/capture-session-transcript.md** — rewrite Statuses section:
   - Remove push-related statuses (pushed, push-failed-abandoned, prior-orphans-abandoned, push-skipped-non-flush-diff, already-present, push-skipped-fetch-failed, push-skipped-fetch-failed)
   - Update `captured` description to remove the post-commit push paragraph.

7. **scripts/test-larch-log.sh** — add regression test: larch-log-flush.sh exits 0 without committing when post-merge-sentinel file exists.

8. **scripts/larch-log-flush.md** — add invariant: no-ops when post-merge-sentinel exists.

9. **skills/implement/SKILL.md** Step 18 — update capture-session-transcript call paragraph to remove mention of post-commit push/reset logic.

### Edge cases
- The sentinel is written before `advance_phase postmerge`; postmerge and teardown run after sentinel exists, so larch-log-flush.sh is a no-op for all remaining commits.
- If ship-pr.sh is interrupted before writing the sentinel, larch-log-flush.sh may still fire once on the next restart. Acceptable: the issue is phantom commits, and the sentinel protects the steady-state path.


## Test plan
Run `make test-capture-session-transcript test-larch-log` after changes. Grep for any remaining `git push origin main` in scripts/ and skills/*/scripts/.
