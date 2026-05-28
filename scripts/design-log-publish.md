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
   are skipped; `plan-review/` and `render-cache/` subtrees fail closed on any
   symlink anywhere in them.
   Files whose basename matches the suffix deny-list are skipped before any
   trim/redact work (`design_artifact_excluded`, narrows the
   `round_artifact_included` deny patterns in `scripts/larch-log.sh` for
   `/implement` to the sidecar/operational-scratch family that also appears
   in design tmpdirs): `*.sidecar`, `*.dirty-tree`, `*.untracked-baseline`,
   `*.done`, `*.diag`, `*.events.jsonl`, `*-output.txt.prompt`,
   `*-output-*.txt.prompt`. Other
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
   `--reason pause` uses `pause design run` in the subject; the default
   `--reason final` uses `flush design run`.
7. Pushing the disposable branch, creating a PR with `gh pr create --head`
   (not `create-pr.sh`), squash-merging with `gh pr merge --squash --admin
   --delete-branch`, then `git worktree remove --force`.

## Pause Reason

`--reason final|pause` defaults to `final`. Pause callers MUST pass
`--reason pause`.

Pause publishes differ in four ways:

- Commit subject: `chore(larch-logs): pause design run <RUN_ID> [skip ci]`.
- Manifest: when there is a non-empty commit to publish, `manifest.json` is
  updated with `.paused = true`. The empty-porcelain early-exit path does not
  force a manifest rewrite; the issue-body `larch:design-pause` marker remains
  the canonical paused signal.
- Branch reuse: the script best-effort fetches an existing
  `origin/larch-log-design-<RUN_ID>` ref before creating the disposable worktree
  and pushes with `git push --force-with-lease`.
- `.completed/`: any regular files under `$DESIGN_TMPDIR/.completed/` with
  `step-*` basenames are staged to
  `larch-logs/design/<RUN_ID>/.completed/` through the normal redaction path.

## PR creation exception

This script is the documented disposable-worktree exception to the repository's
default PR creation path. It pushes a custom `larch-log-design-<RUN_ID>` branch
from a temporary worktree and owns its own PR lookup, merge, recovery-branch,
and cleanup semantics, so it invokes `gh pr create --head` directly instead of
delegating to `scripts/create-pr.sh`.

The PR body is still file-backed: the script writes the short body into a
`mktemp` file before `git push` and passes that path via `--body-file`. Writing
the body file before push ensures a local temp-file failure cannot leave a
pushed branch that never had a valid PR body prepared.

## Output

On stdout (parseable `KEY=value` lines):

**Exit code**: `PUBLISH_OK=true|false` remains the stdout contract. Exit `0` on
all expected failures before a successful `git push`, and on post-push paths
that still parse cleanly via stdout alone. Exit `1` on `git push` failure,
`gh pr create` failure after push (when list recovery also fails), and
`gh pr merge` failure after a successful create — while still emitting
`PUBLISH_OK=false` (and `RECOVERY_BRANCH=…` when applicable). Callers that
already parse `PUBLISH_OK` need no change; callers that want fail-closed
signaling can additionally check the exit code.

Per-script `larch-quiet-*-*.log` files in `$DESIGN_TMPDIR` are excluded from
top-level artifact staging (`design_artifact_excluded`); they are published
exclusively under `breadcrumbs/` via `larch_log_publish_breadcrumbs_shared`.

| Key | Meaning |
|-----|---------|
| `PUBLISH_OK` | `true` when the publish + merge tail succeeded; `false` on validation failure, init/copy/redact failure, git/gh errors, or merge refusal (`policy_denied`, etc.). |
| `PR_NUMBER` | GitHub PR number when known (may be set when `PUBLISH_OK=false` if create succeeded but merge failed). |
| `PR_URL` | PR URL when known. |
| `RECOVERY_BRANCH` | Recovery ref name when `PUBLISH_OK=false`: `larch-log-design-<RUN_ID>` after a successful push that still needs cleanup, or `larch-log-design-recovery-<RUN_ID>` when push failed and the local commit was preserved only in the consumer clone. |

`--dry-run` validates arguments, confirms `--design-tmpdir` exists, requires
`git` and `gh` on `PATH`, resolves `git rev-parse --show-toplevel` and
`origin/HEAD` read-only (same as a real publish preflight), skips the `jq`
requirement and all mutating git/gh steps, and emits `PUBLISH_OK=true` with
empty `PR_NUMBER` / `PR_URL`.

## Security and token scope

Validates `$DESIGN_TMPDIR` is under the allowlist via `larch_design_tmpdir_validate` immediately after the required-arg check and before any worktree or log-root mkdir; failure routes through `emit_publish_result false; exit 0` to preserve `PUBLISH_OK=false`.

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

`$DESIGN_TMPDIR/plan-review/` is optional. A missing path is success and stages
no files. When present, including as a symlink path caught by the `-L` guard,
it is fail-closed:

- `plan-review` must be a real directory, not a symlink and not a regular file.
- Any symlink anywhere below the resolved physical `plan-review` root fails the
  publish before regular-file enumeration. This catches both symlinked files
  and symlinked intermediate directories; `find -type f -not -type l` is not
  sufficient because `find` does not traverse symlinked directories without
  `-L`.
- Each enumerated file must pass the under-root prefix guard against the
  resolved physical root, matching the `render-cache/` guard.
- A per-file `[[ -L "$f" ]]` recheck immediately before staging closes the
  find-to-stage race window at the leaf-component slot. Parent-directory
  replacement races, where a parent dir is swapped for a symlink between
  enumeration and stage, are not closed; this matches the residual race surface
  in `render-cache/`.
- Top-level round files must match `^round-[1-9][0-9]*/[A-Za-z0-9._+-]+$` and pass
  `design_round_artifact_included(basename)` from `scripts/lib-design-round-artifacts.sh`.
- Files under `^round-[1-9][0-9]*/revise/[A-Za-z0-9._+-]+$` must pass
  `design_round_revise_artifact_included(basename)`.
- Any other path under `plan-review/` emits `larch_err` and `PUBLISH_OK=false`.
- Round numbers are positive integers with no leading zero; `round-0` and `round-01` are rejected.

Edit-in-sync: any allowlist change updates `lib-design-round-artifacts.sh`, this doc,
`plan-review-loop.md`, `scripts/lib-design-round-artifacts.md`, and
`scripts/test-lib-design-round-artifacts.sh` in the same change.

Allowed files are staged through the same trim/redact pipeline as other design
artifacts at `larch-logs/design/<RUN_ID>/plan-review/<relpath>`.

## render-cache symlink rejection

`$DESIGN_TMPDIR/render-cache/` is optional. A missing directory is success and
stages no files. When present, including as a symlink path caught by the `-L`
guard, it is fail-closed against symlinks:

- `render-cache` must be a real directory, not a symlink (including dangling)
  and not a regular file.
- Any symlink anywhere below the resolved physical `render-cache` root fails the
  publish before regular-file enumeration. Same rationale as `plan-review/`:
  this catches both symlinked files, which `find -type f` would silently skip,
  and symlinked intermediate directories, which `find` does not traverse without
  `-L`.
- Each enumerated file must pass the under-root prefix guard against the
  resolved physical root.
- A per-file `[[ -L "$f" ]]` recheck immediately before staging closes the
  find-to-stage race window at the leaf-component slot. Parent-directory
  replacement races, where a parent dir is swapped for a symlink between
  enumeration and stage, are not closed; this is the same residual race surface
  as `plan-review/`.
- No filename allowlist is enforced because render-cache content schema is open.
  The suffix deny-list inside `design_publish_stage_file` (`*.sidecar`,
  `*.events.jsonl`, etc.) is preserved unchanged.

Allowed files are staged through the same trim/redact pipeline at
`larch-logs/design/<RUN_ID>/render-cache/<relpath>`.

## Tests

Offline harness: `scripts/test-design-log-publish.sh` (Makefile target
`test-design-log-publish`).
