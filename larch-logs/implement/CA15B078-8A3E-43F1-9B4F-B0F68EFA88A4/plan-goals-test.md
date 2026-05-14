## Goal
Replace dedicated larch-logs flush commits with a tail-call pattern on each commit primitive, and remove the CI paths-ignore filter

## Implementation Plan

### Goal
Replace dedicated `chore(larch-logs):` flush commits (and the CI-skip yaml trick that hides them) with a tail-call scheme: each of the 4 commit primitives appends a log-flush commit right after its own commit. Remove the dedicated flush call sites and CI filter. Keep --no-logs-commit, rewiring it via LARCH_NO_LOGS_COMMIT env var exported from ship-pr.sh.

### Step 1 — Create `scripts/larch-log-flush.sh` (new tail-call helper)
- No-op when IMPLEMENT_TMPDIR is unset/empty
- No-op when LARCH_NO_LOGS_COMMIT=true
- Reads run_id from `$IMPLEMENT_TMPDIR/session-id`
- Calls `larch-log.sh commit --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$run_id"` (no --no-push, since we're removing that flag)
- All failures silently absorbed (|| true); exits 0 always
- Uses SCRIPT_DIR to locate larch-log.sh in the same scripts/ directory

### Step 2 — Add tail-call to `scripts/git-commit.sh`
- After `git commit --file "$TMPFILE"` line, add:
  `"$(dirname "${BASH_SOURCE[0]}")/larch-log-flush.sh" || true`
- This fires after every successful business commit

### Step 3 — Add tail-call to `scripts/git-amend-add.sh`
- After `git commit --amend --no-edit`, add the same flush call

### Step 4 — Add tail-call to `.claude/skills/bump-version/scripts/apply-bump.sh`
- In the success branch after `if git commit -m "$COMMIT_MSG" --quiet; then`, before `echo "APPLIED=true"`, add the flush call
- Flush path: `"$(dirname "${BASH_SOURCE[0]}")/../../../scripts/larch-log-flush.sh" || true`
  Actually, apply-bump.sh is in `.claude/skills/bump-version/scripts/`, so relative path to scripts/ is `../../../../scripts/` from pwd, or use BASH_SOURCE to navigate:
  `FLUSH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../scripts" && pwd)/larch-log-flush.sh"`
  Or simpler: navigate 4 levels up from apply-bump.sh location.
  Actually: apply-bump.sh is at `.claude/skills/bump-version/scripts/apply-bump.sh`
  Relative to that: `../../../../scripts/larch-log-flush.sh`

### Step 5 — Add tail-call to `skills/implement/scripts/step2-implement.sh`
- After `rm -f "$COMMIT_STDERR_FILE"` (which follows the successful dispatcher commit), add:
  `"$PLUGIN_ROOT/scripts/larch-log-flush.sh" || true`
- $PLUGIN_ROOT is already defined in step2-implement.sh

### Step 6 — Drop `--no-push` from `scripts/larch-log.sh commit`
- Remove NO_PUSH=false init, --no-push flag parse, and the `if [ "$NO_PUSH" = false ]; then git push; fi` block
- Update usage string to remove `[--no-push]`
- No-push is now the only behavior

### Step 7 — Update `scripts/refresh-run-logs.sh`
- Remove `--no-push` from the `larch-log.sh commit` call (line 65)

### Step 8 — Update `scripts/larch-log.md`
- Remove the `--no-push discipline` section or update it to say no-push is now always the behavior

### Step 9 — Update `scripts/ship-pr.sh`
- After `NO_LOGS_COMMIT` is parsed, add `export LARCH_NO_LOGS_COMMIT="$NO_LOGS_COMMIT"` so subprocesses inherit it
- Remove the rebase-phase larch-log.sh commit call (in run_rebase_rebump, step 1b ~line 800-807)
- Remove the ci-merge-phase larch-log.sh commit call (~line 944-955)
- Remove the postmerge-phase larch-log.sh commit call (~line 1130-1142) and its record_failure line

### Step 10 — Update `scripts/implement-finalize.sh`
- Remove the teardown larch-log.sh commit calls (lines ~1588-1593: the pr_closed branch and the no-pr branch)

### Step 11 — Update `.github/workflows/ci.yaml`
- Remove `paths-ignore: - 'larch-logs/**'` from pull_request trigger
- Remove `paths-ignore: - 'larch-logs/**'` from push trigger

### Step 12 — Update `.github/workflows/release-tag.yaml`
- Remove `paths-ignore: - 'larch-logs/**'` from push trigger

### Step 13 — Update `skills/implement/SKILL.md`
- In `--no-logs-commit` flag description: update to say it now suppresses tail-call flushes (via LARCH_NO_LOGS_COMMIT env var) when primitives are invoked within ship-pr.sh subprocess tree
- Remove `--no-push` from the pre-bump log flush call in Step 7a tail (since larch-log.sh commit no longer accepts --no-push)

### Step 14 — Update `scripts/ship-pr.md`
- Remove the flush-call documentation from the ci-merge and postmerge descriptions
- Add note about LARCH_NO_LOGS_COMMIT env var export and tail-call behavior
- Update --no-logs-commit description to reflect new scope


## Test plan
- `make lint` (pre-commit + agent-lint)
- Check git-commit.sh, git-amend-add.sh, apply-bump.sh, step2-implement.sh all have flush tail-calls
- Check ship-pr.sh no longer has the 3 dedicated larch-log.sh commit calls
- Check implement-finalize.sh no longer has teardown larch-log.sh commit calls
- Check CI yaml files no longer have paths-ignore: 'larch-logs/**'
