## Plan

### Feature
feat(/design): append [PLANNED] to tracking issue title on completion + flush design run logs to a dedicated log-only PR.

### Files to modify/create

**1. `scripts/tracking-issue-write.sh`**
- `state_to_prefix()`: add `planned) printf '[PLANNED] ' ;;`
- `strip_lifecycle_prefix()`: add `'[PLANNED] '*) printf '%s' "${t#\[PLANNED\] }" ;;`
- Error message: update to `expected in-progress|done|stalled|planned`
- `usage()` rename line and "Rename semantics" header comment: add `planned`/`[PLANNED]`
- `CUR_CANON_PREFIXES` case block: add `'[PLANNED] '*) CUR_CANON_PREFIXES='[PLANNED] ' ;;`

**2. `scripts/tracking-issue-write.md`**
- Update `rename` argv usage line and "Rename semantics" section to include `planned`/`[PLANNED]`

**3. `scripts/lib-title-markers.sh`**
- `insert_signal_marker()`: add `'[PLANNED] '*) printf '[PLANNED] [%s] %s' "$marker" "${title#\[PLANNED\] }" ;;`

**4. `skills/fix-issue/scripts/find-lock-issue.sh`**
- `has_managed_lifecycle_prefix()`: add `[PLANNED]` to the prefix-check pattern
- Add harness coverage in the fix-issue test harness

**5. `scripts/design-log-publish.sh`** (new)
Interface: `design-log-publish.sh --design-tmpdir PATH --run-id ID --issue N --repo OWNER/REPO [--dry-run]`

Steps:
1. Validate `--run-id` via `larch_log_validate_slug`
2. Resolve REPO_ROOT via `git rev-parse --show-toplevel`
3. Resolve default base branch: `git symbolic-ref refs/remotes/origin/HEAD | sed 's#refs/remotes/origin/##'`
4. Create git worktree on dedicated `larch-log-design-$RUN_ID` branch from `origin/$ORIGIN_DEFAULT`
5. `larch-log.sh init` for full schema-2 manifest.json in worktree
6. Copy DESIGN_TMPDIR files (depth-1 + render-cache/) with: sidecar trimming (CMD_JSON from .meta, .result from *-output*.json) → redact-tmpdir-paths.sh → redact-secrets.sh; skip symlinks; fail closed on trim error
7. `git commit -m "chore(larch-logs): flush design run $RUN_ID [skip ci]"` in worktree
8. `git push origin larch-log-design-$RUN_ID`
9. `gh pr create --head larch-log-design-$RUN_ID --base $ORIGIN_DEFAULT ...`
10. `gh pr merge $PR_NUMBER --squash --admin --delete-branch`
11. `git worktree remove --force`
12. Emit: `PUBLISH_OK=true|false`, `PR_NUMBER`, `PR_URL`

**6. `scripts/design-log-publish.md`** (new) — sibling contract doc

**7. `scripts/test-design-log-publish.sh`** (new) — offline harness (happy path, worktree isolation, sidecar trimming, slug validation, dry-run, failure recovery)

**8. `scripts/test-design-log-publish.md`** (new) — sibling stub

**9. `scripts/test-tracking-issue-write.sh`** — add `planned` state + idempotency test cases

**10. `skills/design/SKILL.md`**
- Step 0b: parse `SESSION_ID` from `session-setup.sh` output alongside `SESSION_TMPDIR`
- Step 5b: add REPO resolution + `[PLANNED]` rename + `design-log-publish.sh` call after `plan-block-write.sh`; use `printf` not `print` for warnings; use `${CLAUDE_PLUGIN_ROOT}/scripts/...` prefix
- Step 0b clarify-loop exit: add same rename + publish snippet before exit 0

**11. `docs/run-logs.md`** — add `design/<RUN_ID>/` to Directory structure

**12. `SECURITY.md`** — add design log redaction and `--admin` token scope notes

### Approach

**`[PLANNED]` prefix**: five-location edit in `tracking-issue-write.sh` + one in `lib-title-markers.sh` + `tracking-issue-write.md` sibling update + `find-lock-issue.sh` exclusion (so /fix-issue treats [PLANNED] issues as machine-managed).

**Design log publish**: dedicated git worktree on `larch-log-design-$RUN_ID` branch from `origin/HEAD`. `larch-log.sh init` produces full schema-2 manifest. Artifact copy uses sidecar trimming (CMD_JSON/.result) + two-stage redaction, fail-closed on errors. Git commit carries `[skip ci]`. PR created via `gh pr create --head` (not `create-pr.sh`) to avoid existing-PR fast-path conflict. `gh pr merge --squash --admin --delete-branch` merges and cleans up. Original working tree branch is never touched.

**SESSION_ID**: parsed in Step 0b. **REPO**: resolved in Step 5b. **Clarify path**: also runs rename + publish.

### Edge cases
- SESSION_ID empty → skip publish with warning
- Worktree cleanup failure → operator uses `git worktree remove --force`
- Sidecar trim failure (jq absent) → fail closed, `PUBLISH_OK=false`
- PR already exists for log branch → proceed with merge

### Failure modes
1. `gh pr merge --admin` fails (`policy_denied`) → `PUBLISH_OK=false`; logs committed locally
2. Redaction failure → abort before commit
3. `larch-log.sh init` fails → abort

### Testing strategy
- `test-tracking-issue-write.sh`: `planned` state + idempotency
- `test-design-log-publish.sh`: happy path, worktree isolation, sidecar trimming, dry-run, failure cases
- Manual smoke test: `/design <issue>` → `[PLANNED]` on issue title + `larch-logs/design/<run-id>/` in remote main

## Acceptance

All 12 accepted review findings addressed. F6 (neutral) and F14 (exonerated) not implemented.

diff_lines: 420
