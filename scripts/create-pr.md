# create-pr.sh contract

## Purpose

Push the current branch to `origin` and create or detect a GitHub pull request. Two paths:

- **Existing-PR fast-path**: when `gh pr view` reports an OPEN PR for the current branch, push any new local commits and emit `PR_STATUS=existing`. Used by `/implement` Step 9b on resumed runs and on every CI+rebase+merge iteration where the branch already has a PR.
- **New-PR path**: no OPEN PR exists for the current branch. Push the branch (creates the upstream ref) and `gh pr create` with the supplied title/body. Emit `PR_STATUS=created`.

Both paths emit the same four `PR_*` keys on stdout so downstream consumers parse one contract regardless of path.

## Interface

```
create-pr.sh --title TEXT --body-file FILE [--draft] [--repo OWNER/REPO] [--base BASE_REF]
```

Flags:

- `--title TEXT` (required) — PR title. Recommended under 70 characters; not enforced.
- `--body-file FILE` (required) — path to a markdown file containing the PR body. File must exist; checked at startup. On the new-PR path the body is copied through `scripts/redact-tmpdir-paths.sh` and the redacted temp file is forwarded to `gh pr create --body-file`; missing or failing redaction exits 2. The file is ignored on the existing-PR fast-path (existing PR body is not updated by this script — see `gh-pr-body-update.sh` for that operation).
- `--draft` (optional, no value) — pass `--draft` to `gh pr create` so a fresh PR is opened in draft state. Has no effect on the existing-PR fast-path (an already-open PR's draft state is not changed).
- `--repo OWNER/REPO` (optional) — pass `--repo` to every `gh pr view` / `gh pr create` call. Used by `/implement --forked` so PR detection and creation target the fork (`origin`) even when `gh` would otherwise resolve the upstream repository. When omitted, the script tries `scripts/resolve-repo.sh` and threads the resolved repo; if resolution fails, it preserves the prior ambient-repo fallback.
- `--base BASE_REF` (optional) — base branch for a freshly created PR. When omitted, the new-PR path asks `gh repo view [--repo OWNER/REPO] --json defaultBranchRef --jq '.defaultBranchRef.name'` and falls back to `main` if detection fails or returns empty. The existing-PR fast-path does not need a base branch and skips detection.

## Output contract (KEY=value on stdout)

### Success (both paths)

```
PR_NUMBER=<integer>
PR_URL=<full GitHub PR URL>
PR_TITLE=<title text>
PR_STATUS=created|existing
```

`PR_STATUS=created` indicates a fresh PR was opened by this run. `PR_STATUS=existing` indicates an OPEN PR was already present and the script only synced the branch tip.

### Failure

Failure is signalled exclusively via non-zero exit code + a human-readable `ERROR:` message on stderr. The script does NOT emit failure key=value lines on stdout — `/implement` Step 9b's parser detects failure by exit code.

## Pre-push clean-tree guard

Before any push attempt, `create-pr.sh` runs `git status --porcelain` and aborts with exit 1 if the working tree is dirty. This prevents silent data loss: uncommitted changes (e.g., inline OOS-fold edits applied between commit boundaries) would otherwise be excluded from the push and therefore missing from the merged PR. The check runs once at script entry, covering all three push sites (new-PR path, existing-PR fast-path plain push, existing-PR fast-path force-push escalation). The error message lists the dirty paths so the operator knows exactly what to stage and commit before retrying.

## Exit codes

| Exit | Meaning |
|------|---------|
| 0    | PR created or pre-existing PR detected; remote branch confirmed up-to-date with local. |
| 1    | Push failed (includes dirty-tree abort). Either path: stderr carries the underlying git rejection or the list of uncommitted paths. |
| 2    | Argument validation failed, branch detection failed (detached HEAD), `gh pr create` failed, or PR number/URL extraction failed. |

## PR body redaction

`create-pr.sh` removes larch session tmpdir literals from fresh PR bodies via `scripts/redact-tmpdir-paths.sh` before invoking `gh pr create`. This covers `$IMPLEMENT_TMPDIR` references that may appear in generated test output, diagrams, or execution notes. Secret-family redaction is owned by upstream compose sites and downstream helpers; this script currently adds only the tmpdir-path pass because it had no pre-existing secret-redaction pipeline.

## Existing-PR fast-path push semantics (issue #837)

On the existing-PR fast-path, the script attempts a plain `git push -u origin HEAD` first. If the plain push succeeds (fast-forward or no-op), the script proceeds to emit the `PR_*` lines and exits 0.

If the plain push fails (commonly non-fast-forward after a history rewrite — e.g., `/implement` Step 12's rebase + re-bump path), the script escalates to `git-force-push.sh` (force-with-lease + race-recovery + single retry). Before invoking the helper, the script defensively populates the local `origin/$BRANCH` ref via `git fetch origin "$BRANCH"` and sets upstream tracking via `git branch --set-upstream-to=origin/$BRANCH "$BRANCH"`, since `git-force-push.sh`'s `git push --force-with-lease` (no refspec) requires both. If the helper exits non-zero (`STATUS=diverged_retry_failed` — diverged history that lease cannot reconcile), this script exits 1 with the helper's stderr surfaced. The helper's stdout (`BRANCH=`/`PUSHED=`/`STATUS=` keys) is suppressed to `/dev/null` so the documented `PR_*` stdout contract this script publishes stays intact.

Prior to the #837 fix, the fast-path's push line read `git push -u origin HEAD >/dev/null 2>&1 || true`, silently swallowing every push failure (non-fast-forward, lease failures, network errors). That violated the documented exit-1-on-push-failure contract on this path and caused `/implement` to emit `PR_STATUS=existing` while origin's branch tip was actually stale. The current fail-closed behavior is the documented contract.

## New-PR path push semantics

The new-PR path uses plain `git push -u origin HEAD` (no force semantics) — the branch is freshly named and origin has no prior tip on it, so there is no lease scenario to consider. Push failure exits 1 with stderr surfaced.

## Exit-code parity invariant

Both paths surface push failure as exit 1 with stderr, and both paths surface success as exit 0 with the four `PR_*` keys on stdout. Callers depend on this parity — `/implement` Step 9b runs the same parser regardless of `PR_STATUS=created|existing`.

## Sibling files

- `scripts/git-force-push.sh` — invoked on the existing-PR fast-path's escalation branch.
- `scripts/gh-pr-body-update.sh` — used by `/implement` Step 9b to update an existing PR's body when `PR_STATUS=existing` (since this script does not update the body of pre-existing PRs).

## PR-create failure diagnostics

On non-zero exit from `gh pr create`, the script always emits a diagnostic `ERROR:` line to stderr that includes: the redacted argv used, the captured stderr from `gh pr create`, the exit code, and the last 10 lines of stdout. If all three content fields are empty, the message contains the stub `(no diagnostic captured; gh pr create exited <N> with no output. Manual investigation required.)` so operators never see an empty backtick error block in execution-issues output.

## Test harness

`scripts/test-create-pr.sh` uses temporary git repositories and a PATH-stubbed `gh` binary to assert that `--repo` is threaded through every `gh pr view` and `gh pr create` path, including existing-PR title backfill and PR-number fallback. It also covers explicit `--base`, detected default-branch base, fallback-to-`main` base selection on the new-PR path, the empty-stderr diagnostic case (asserts that the error block is non-empty when `gh pr create` exits with no output), and the pre-push clean-tree guard (clean tree proceeds; tracked-modified and untracked-file dirty trees exit non-zero with a descriptive error).

## Edit-in-sync rules

When changing `scripts/create-pr.sh`:

- Update this file (`scripts/create-pr.md`) in the same PR if any of the following changes:
  - Stdout contract (`PR_*` keys, format).
  - Exit code semantics.
  - Push semantics on either path (especially the existing-PR fast-path's escalation policy).
  - The set of CLI flags or their defaults.
- Verify `/implement` Step 9b's parser in `skills/implement/SKILL.md` still parses the four `PR_*` keys and continues to abort on non-zero exit.
- Verify the helper invocation path (`$SCRIPT_DIR/git-force-push.sh`) is robust to the caller's CWD — `SCRIPT_DIR` is derived once at the top of the script.
