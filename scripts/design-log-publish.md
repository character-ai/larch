# design-log-publish.sh contract

`scripts/design-log-publish.sh` flushes a completed `/design` session directory
(`$DESIGN_TMPDIR`) into `larch-logs/design/<RUN_ID>/` on the repository default
branch by:

1. Validating `--run-id` with the same slug rules as `scripts/larch-log.sh`
   (`larch_log_slug_is_valid` / `larch_log_validate_slug` family: ASCII letters,
   digits, `.`, `_`, `-`; reject empty, `..`, `/`, `\`, leading `.`).
2. Resolving `REPO_ROOT` via `git rev-parse --show-toplevel` and the default
   base branch via `git symbolic-ref refs/remotes/origin/HEAD` (same family as
   `larch-log.sh commit`'s default-branch guard — not a `main`-only string
   compare).
3. Creating a disposable git worktree on branch `larch-log-design-<RUN_ID>`
   from `origin/<default>`. Before `git worktree add`, the script refuses to
   start when that branch name is already checked out in another worktree, and
   it does not ignore a failed `git branch -D` for an existing local branch with
   the same name. Unlike `/implement` and `/fix-issue`, `/design` does not
   globally serialize publishers: two concurrent runs must not share the same
   `RUN_ID` slug on one clone, or they will collide on this branch/worktree slot.
4. Running `larch-log.sh init` under `larch-logs/` in that worktree (schema v2
   `manifest.json` for skill `design`).
5. Copying design artifacts: top-level regular files (maxdepth 1), the strict
   `plan-review/round-<N>/findings-classification.tsv` allowlist, plus all
   regular files under `render-cache/` (recursive). Symlinks at the top level
   are skipped; `render-cache/` itself must be a real directory (not a symlink).
   Files whose basename matches the suffix deny-list are skipped before any
   trim/redact work (`design_artifact_excluded`, narrows the
   `round_artifact_included` deny patterns in `scripts/larch-log.sh` for
   `/implement` to the sidecar/operational-scratch family that also appears
   in design tmpdirs): `*.sidecar`, `*.dirty-tree`, `*.untracked-baseline`,
   `*.done`, `*.diag`, `*-output.txt.prompt`, `*-output-*.txt.prompt`. Other
   `/implement`-specific deny patterns (`coder-output.log`, `coder-codex.log`,
   `cursor-specialist-*-output.txt`, `*-vote-prompt.txt`, the known empty
   placeholders) are intentionally NOT included — those basenames do not
   appear in design tmpdirs. All other basenames pass through (deny-only
   model — `/design` has many file types `/implement` does not, so the design
   path is default-allow). Each included file is trimmed then redacted:
   `*.meta` strips leading `CMD_JSON=`
   lines (`larch_redact_strip_meta_cmd_json`); files whose names match
   `*-output*.json` delete a top-level `.result` object when valid JSON
   (`larch_redact_strip_json_result`, fail-closed on trim error); other paths
   copy through without that JSON trim; then `redact-tmpdir-paths.sh` and
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

## plan-review allowlist

`$DESIGN_TMPDIR/plan-review/` is optional. A missing or empty directory is
success and stages no files. When present, it is fail-closed:

- `plan-review` must be a real directory, not a symlink and not a regular file.
- Any symlink anywhere below the resolved physical `plan-review` root fails the
  publish before regular-file enumeration. This catches both symlinked files
  and symlinked intermediate directories; `find -type f -not -type l` is not
  sufficient because `find` does not traverse symlinked directories without
  `-L`.
- Each enumerated file must pass the under-root prefix guard against the
  resolved physical root, matching the `render-cache/` guard.
- The relativized path must match the anchored regex
  `^round-[1-9][0-9]*/findings-classification\.tsv$`. Round numbers are
  positive integers with no leading zero; `round-0` and `round-01` are rejected.
- Any unexpected file under `plan-review/` emits `larch_err` and
  `PUBLISH_OK=false`.

Allowed files are staged through the same trim/redact pipeline as other design
artifacts at `larch-logs/design/<RUN_ID>/plan-review/<relpath>`.

## Tests

Offline harness: `scripts/test-design-log-publish.sh` (Makefile target
`test-design-log-publish`).
