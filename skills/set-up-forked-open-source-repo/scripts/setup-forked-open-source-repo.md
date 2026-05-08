# setup-forked-open-source-repo.sh

## Purpose

`setup-forked-open-source-repo.sh` configures the current git checkout for the
single-clone upstream/fork contribution workflow. It verifies a GitHub.com fork,
optionally syncs the fork from upstream, rewires local remotes so `origin`
points at the fork and `upstream` points at upstream, disables upstream pushes,
sets `main` to track `origin/main`, and prints the final PR workflow reminder.

Primary caller: `skills/set-up-forked-open-source-repo/SKILL.md`.

## CLI

```bash
setup-forked-open-source-repo.sh --upstream owner/repo --fork owner/repo [--mirror-confirmed] [--init-submodules]
```

The script operates only on `git rev-parse --show-toplevel` for the caller's
current working directory. It does not scan sibling clones. The upstream and
fork arguments must be GitHub `owner/repo` names; GitHub Enterprise and other
hosts are intentionally out of scope.

## Invariants

- Refuse before mutation when the worktree is dirty, the checkout is not
  `main`, local `main` is ahead of `origin/main`, local and remote main have
  diverged, a git operation is in progress, or local `refs/heads/main` is
  absent.
- Treat only explicit fork not-found diagnostics from `gh repo view` as a
  clean fork-missing result. Auth, network, SSO, rate-limit, and other API
  failures exit non-zero after stderr is routed through `scripts/redact-secrets.sh`.
- Verify `parent.nameWithOwner` exactly matches the declared upstream before
  any mirror push.
- Probe `refs/heads/main` explicitly for both upstream and fork; never fall
  back to `HEAD` or `master`.
- Mirror-sync only when upstream and fork `refs/heads/main` differ, after
  TTY confirmation or `--mirror-confirmed`, and after a second pre-push
  TOCTOU probe confirms neither SHA moved.
- Use a fresh temporary mirror clone and scoped refspecs:
  `+refs/heads/*:refs/heads/*` and `+refs/tags/*:refs/tags/*` with `--prune`.
  The script never runs `git push --mirror` from the user's working clone.
- Classify local remotes using fetch URLs only; push URLs are checked
  separately so the disabled upstream push sentinel remains idempotent.
- Refuse ambiguous remote layouts, including non-GitHub URLs, pre-existing
  unexpected `upstream`, multiple fetch URLs, multiple push URLs, duplicate fork
  remotes, or remotes pointing at neither upstream nor fork.
- Snapshot `remote.*` and `branch.*` git config before remote mutation. Any
  failure inside the remote phase restores that snapshot best-effort; rollback
  failure emits a `RECOVERY_REPORT` diagnostic.
- Set `remote.upstream.pushurl` to the invalid-scheme sentinel
  `larch-disabled://upstream-push-disabled`.
- Initialize submodules only when `--init-submodules` is present. Failure is
  fatal on that opt-in path.

## Stable Results

The script emits one or more stable stdout markers:

- `SETUP_FORKED_REPO_RESULT=fork_missing` — the fork does not exist; no local
  mutation was performed.
- `SETUP_FORKED_REPO_RESULT=mirror_skipped_in_sync` — fork `main` already
  matched upstream `main`.
- `SETUP_FORKED_REPO_RESULT=mirror_synced` — fork branches and tags were synced
  from upstream through the scoped destructive push.
- `SETUP_FORKED_REPO_RESULT=ok` — local remotes and branch tracking verified.

## Test Seam

The offline harness sets these URL override variables so the same coordinator
can exercise mirror logic against local bare repositories:

- `LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_HTTPS`
- `LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_SSH`
- `LARCH_FORKED_REPO_URL_OVERRIDE_FORK_HTTPS`
- `LARCH_FORKED_REPO_URL_OVERRIDE_FORK_SSH`

Production runs leave them unset and derive deterministic GitHub SSH/HTTPS
URLs from the `owner/repo` arguments.

The harness also uses `LARCH_FORKED_REPO_INJECT_FAILURE` for rollback cases.
Recognized values are `after-rename-origin-upstream`, `fetch`, and `rollback`.

## Harness And Makefile

`test-setup-forked-open-source-repo.sh` is the offline regression harness and
is wired through `make test-set-up-forked-open-source-repo`. The target is part
of one `test-harnesses-N` shard; `make test-harness-shards-coverage` verifies
the partition.

## Edit In Sync

Behavior changes must update this contract, the pointer stubs
`lib-remotes.md` and `test-setup-forked-open-source-repo.md` when relevant, the
harness, `SECURITY.md` for destructive-sync posture changes, and the skill body
when the public invocation contract changes.
