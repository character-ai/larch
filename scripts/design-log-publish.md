# design-log-publish.sh contract

`scripts/design-log-publish.sh` flushes a completed `/design` session directory
(`$DESIGN_TMPDIR`) into `larch-logs/design/<RUN_ID>/` on the repository default
branch by:

1. Validating `--run-id` with the same slug rules as `scripts/larch-log.sh`
   (`larch_log_validate_slug` family: ASCII letters, digits, `.`, `_`, `-`;
   reject empty, `..`, `/`, `\`, leading `.`).
2. Resolving `REPO_ROOT` via `git rev-parse --show-toplevel` and the default
   base branch via `git symbolic-ref refs/remotes/origin/HEAD` (same family as
   `larch-log.sh commit`'s default-branch guard — not a `main`-only string
   compare).
3. Creating a disposable git worktree on branch `larch-log-design-<RUN_ID>`
   from `origin/<default>`.
4. Running `larch-log.sh init` under `larch-logs/` in that worktree (schema v2
   `manifest.json` for skill `design`).
5. Copying design artifacts: top-level regular files (maxdepth 1) plus all
   regular files under `render-cache/` (recursive). Symlinks are skipped.
   Each file is trimmed then redacted: `*.meta` strips leading `CMD_JSON=`
   lines (`larch_redact_strip_meta_cmd_json`); every `*.json` file deletes a
   top-level `.result` object when valid JSON (`larch_redact_strip_json_result`,
   fail-closed on trim error); then `redact-tmpdir-paths.sh` and
   `redact-secrets.sh` (in-process pipeline, same redactors as
   `larch_log_redact_file` without the larch-log stdout contract).
6. Committing `larch-logs/design/<RUN_ID>/` with message containing `[skip ci]`.
7. Pushing the disposable branch, creating a PR with `gh pr create --head`
   (not `create-pr.sh`), squash-merging with `gh pr merge --squash --admin
   --delete-branch`, then `git worktree remove --force`.

## Output

On stdout (parseable `KEY=value` lines):

| Key | Meaning |
|-----|---------|
| `PUBLISH_OK` | `true` when the publish + merge tail succeeded; `false` on validation failure, init/copy/redact failure, git/gh errors, or merge refusal (`policy_denied`, etc.). |
| `PR_NUMBER` | GitHub PR number when known (may be set when `PUBLISH_OK=false` if create succeeded but merge failed). |
| `PR_URL` | PR URL when known. |
| `RECOVERY_BRANCH` | Disposable branch name (`larch-log-design-<RUN_ID>`) when `PUBLISH_OK=false` after `git push` succeeded (remote may need operator cleanup). |

`--dry-run` validates arguments, confirms `--design-tmpdir` exists, requires
`git` and `gh` on `PATH`, resolves `git rev-parse --show-toplevel` and
`origin/HEAD` read-only (same as a real publish preflight), skips the `jq`
requirement and all mutating git/gh steps, and emits `PUBLISH_OK=true` with
empty `PR_NUMBER` / `PR_URL`.

## Security and token scope

Design log bytes follow the same tmpdir + secrets redaction pipeline as
implement round artifacts. `gh pr merge --admin` bypasses branch-protection
rules that require reviews or status checks; it requires a `gh` OAuth token
with `repo` (or equivalent) including admin-merge privileges. Consumer orgs that
forbid admin merges will see merge failures (`PUBLISH_OK=false`) while the
commit may still exist on the pushed disposable branch — operators reconcile
manually. When `git push` succeeds but PR create/merge fails, stderr notes the
remote branch and stdout may include `RECOVERY_BRANCH=…` for automation. See
`SECURITY.md` for the consolidated note.

## Tests

Offline harness: `scripts/test-design-log-publish.sh` (Makefile target
`test-design-log-publish`).
