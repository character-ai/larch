# setup-forked-open-source-repo.sh

## Purpose

`setup-forked-open-source-repo.sh` configures the current git checkout for the
single-clone upstream/fork contribution workflow. It verifies a fork on the
resolved GitHub-compatible host, optionally syncs the fork from upstream,
rewires local remotes so `origin` points at the fork and `upstream` points at
upstream, disables upstream pushes, sets `main` to track `origin/main`, and
prints the final PR workflow reminder.

Primary caller: `skills/set-up-forked-open-source-repo/SKILL.md`.

## CLI

```bash
setup-forked-open-source-repo.sh --upstream owner/repo --fork owner/repo [--mirror-confirmed] [--init-submodules]
```

The script operates only on `git rev-parse --show-toplevel` for the caller's
current working directory. It does not scan sibling clones. The upstream and
fork arguments are `owner/repo` names; the host is resolved from the stored
`origin` URL when present and defaults to `github.com` otherwise.

## Prerequisites

- `git` and `gh` (authenticated against the resolved host; `github.com` is the
  default).
- `jq` on `PATH`. `phase_preflight` runs `command -v jq` and aborts with an
  actionable message before any GitHub or remote-mutation step. The skill
  body advertises this to operators.
- `flock` when available. The correctness lock is an atomic `mkdir` guard under
  the clone's `.git` common directory, so macOS systems without `flock` still
  serialize concurrent runs.

## Trust caveat: stored URLs vs. `url.*.insteadOf`

Remote classification (`lib-remotes::classify_remote_state`) and the
preflight pre-fetch URL gate (`phase_preflight`'s
`normalize_github_url` check on `remote.origin.url`) operate on **stored**
git config URLs — `remote.<name>.url` and `remote.<name>.pushurl`. They do
NOT inspect or compensate for Git's built-in `url.<other>.insteadOf`
transport-time rewriting (set in user/global gitconfig). A rewrite rule
that targets the constructed GitHub URL silently redirects every network
operation the coordinator runs, bypassing the URL-override allowlist and
the `gh repo view` parent guard. The threat model is same-user
attacker / shared-profile inheritance; SECURITY.md "Fork setup
URL-override footgun" is the canonical residual-risk discussion. Same
trust caveat is mirrored in `SKILL.md` so operators see it before
invoking the skill.

## Invariants

- Acquire a non-blocking per-`.git`-common-dir lock before GitHub calls, fetches,
  or remote rewrites. The lock uses `mkdir "$lock_file.d"` as the portable
  mutex and, when available, FD 9 `flock -n` as a secondary visibility layer.
  `release_clone_lock` removes the holder sidecar before releasing the mkdir
  directory and closes FD 9 last, so a successor's holder cannot be removed by
  predecessor cleanup.
- Resolve `GH_HOST` from `origin` before `gh auth status`, export it for all
  later `gh` commands, and pass `--hostname "$GH_HOST"` to the auth check.
  `normalize_github_url` accepts `https://`, `ssh://`, `git://`, and
  `git@host:owner/repo` shapes and returns `<host>\t<owner/repo>` lowercased.
- Refuse before mutation when any linked worktree in the same clone is dirty,
  the checkout is not `main`, local `main` is ahead of `origin/main`, local and
  remote main have diverged, a git operation is in progress in any linked
  worktree, or local `refs/heads/main` is absent. Prunable worktree records are
  skipped when parsing `git worktree list --porcelain`.
- Treat only explicit fork not-found diagnostics from `gh repo view` as a
  clean fork-missing result. Auth, network, SSO, rate-limit, and other API
  failures exit non-zero after stderr is routed through `scripts/redact-secrets.sh`.
- Verify the fork parent matches the declared upstream **case-insensitively**
  before any mirror push. The parser accepts both `parent.nameWithOwner` and
  the split `parent.owner.login` + `parent.name` shape returned by some
  `gh repo view --json parent` responses, preferring non-empty
  `nameWithOwner` when present. The parser type-guards the split-field path
  (`.parent.owner` must be an object) and silences `jq` errors so a malformed
  payload surfaces as a clean `fork parent mismatch` rather than a raw
  `jq` index/type abort. GitHub treats owner/repo as case-insensitive,
  so the gate lowercases both sides before comparing — an operator passing
  `acme/project` with a canonical `Acme/Project` parent on GitHub passes the
  gate, while a genuinely wrong upstream still fails.
- Probe `refs/heads/main` explicitly for both upstream and fork; never fall
  back to `HEAD` or `master`.
- Mirror-sync only when upstream and fork `refs/heads/main` differ, after
  TTY confirmation or `--mirror-confirmed`, and after a second pre-push
  TOCTOU probe confirms neither SHA moved.
- Use a fresh temporary mirror clone and scoped refspecs:
  `+refs/heads/*:refs/heads/*` and `+refs/tags/*:refs/tags/*` with `--prune`.
  The script never runs `git push --mirror` from the user's working clone.
- Validate the post-push fork SHA against the SHA the temporary mirror clone
  actually contained (`git -C "$clone_dir" rev-parse refs/heads/main`), not
  against the pre-confirmation `upstream_sha`. Upstream `main` can advance
  between the TOCTOU re-probe and the mirror clone; checking against the
  stale snapshot would spuriously fail an already-completed sync.
- Classify local remotes using fetch URLs only; push URLs are checked
  separately so the disabled upstream push sentinel remains idempotent.
  Enumerate remotes via `git remote` and resolve each via
  `git config --get-all "remote.$name.url"` / `pushurl`; do not regex flat
  config keys, because dotted remote names (e.g. `my.fork`,
  `remote.my.fork.url`) are silently skipped by a `^remote\.[^.]+\....`
  pattern and would defeat ambiguity classification.
- Refuse ambiguous remote layouts, including non-parseable URLs, mixed-host
  layouts, pre-existing unexpected `upstream`, multiple fetch URLs, multiple
  push URLs, duplicate fork remotes, or remotes pointing at neither upstream nor
  fork. `phase_preflight` refuses multi-URL `origin` before any `gh` call, and
  caches the host-consistent classifier result before `phase_github`.
- Snapshot `remote.*` and `branch.*` git config before remote mutation. Any
  failure inside the remote phase restores that snapshot best-effort; rollback
  failure emits a `RECOVERY_REPORT` diagnostic. The rollback flag
  (`REMOTE_PHASE_ACTIVE`) stays set through `phase_submodules` and
  `phase_verify` and is cleared only after `phase_verify` emits
  `SETUP_FORKED_REPO_RESULT=ok`, so a failed late-phase assertion or a
  partial submodule init still triggers `restore_remote_state`.
- Set `remote.upstream.pushurl` to the invalid-scheme sentinel
  `larch-disabled://upstream-push-disabled`. After remote rewrites, also
  unset `remote.origin.pushurl` so a stale or hostile pushurl carried over
  from a renamed `<named-fork>` remote cannot redirect future
  `git push origin ...` while origin's fetch URL fetches from the declared
  fork.
- Initialize submodules only when `--init-submodules` is present. Failure is
  fatal on that opt-in path.
- Re-check all linked worktrees for dirtiness before fast-forwarding local
  `main` and re-check all linked worktrees for dirtiness or in-progress git
  operations immediately before the destructive fork mirror push.

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

These are **gated behind an explicit opt-in**: the override fires only when
`LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE=1` is also set. Without the opt-in the
override env vars are ignored even if set, and the URLs derive deterministically
from the `--upstream` / `--fork` arguments. The harness exports both the per-URL
overrides and the opt-in. Operators should not export the opt-in in interactive
shells — a stale export combined with a leaked URL override would redirect a
destructive `git push --prune` to whatever URL the env var names, bypassing the
verified `gh repo view` parent guard. See `SECURITY.md` "Fork setup URL-override
footgun".

The harness also uses `LARCH_FORKED_REPO_INJECT_FAILURE` for rollback cases.
Recognized values are `after-rename-origin-upstream`, `fetch`, `rollback`,
and `in-verify`. The `in-verify` token raises a non-zero command (not
`die`/`exit`) inside `phase_verify` so the harness can prove the late-phase
ERR-trap rollback path — see `phase_die` in the coordinator and the
sibling regression assertion in `test-setup-forked-open-source-repo.sh`.

Lock and host test seams:

- `LARCH_FORKED_REPO_FORCE_MKDIR_LOCK=1` bypasses the optional `flock` layer so
  the portable mkdir mutex is exercised directly.
- `LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S=<seconds>` sleeps immediately after lock
  acquisition, allowing contention tests to hold the lock without polling.
- The `gh` stub records `GH_HOST` and `gh auth status --hostname` so github.com
  and GitHub Enterprise flows can assert host forwarding without network IO.

## Harness And Makefile

`test-setup-forked-open-source-repo.sh` is the offline regression harness and
is wired through `make test-set-up-forked-open-source-repo`. It covers the
original remote rewrite, rollback, mirror, and submodule paths plus host-aware
URL parsing, `GH_HOST` forwarding, multi-URL and mixed-host refusal,
github.com baseline behavior, sibling linked-worktree dirty and operation
sentinels, prunable worktree records, portable mkdir contention, mixed-mode
contention, optional flock contention, and lock sidecar cleanup. The target is
part of one `test-harnesses-N` shard; `make test-harness-shards-coverage`
verifies the partition.

## Edit In Sync

Behavior changes must update this contract, the pointer stubs
`lib-remotes.md` and `test-setup-forked-open-source-repo.md` when relevant, the
harness, `SECURITY.md` for destructive-sync posture changes, and the skill body
when the public invocation contract changes.
